"""Swift Tree-sitter parser adapter for iOS projects."""

from __future__ import annotations

from pathlib import Path

import tree_sitter_swift as tsswift
from tree_sitter import Language as TsLanguage
from tree_sitter import Node

from changeblast.adapters.parsers.base import BaseTreeSitterParser
from changeblast.models.common import (
    EdgeKind,
    Language,
    SymbolKind,
    Visibility,
)
from changeblast.models.edge import DependencyEdge
from changeblast.models.symbol import SourceSymbol
from changeblast.ports.parser import ILanguageParserAdapter


class SwiftParserAdapter(BaseTreeSitterParser, ILanguageParserAdapter):
    """Parses Swift source files into unified SourceSymbol and DependencyEdge models."""

    def __init__(self) -> None:
        super().__init__(TsLanguage(tsswift.language()))

    @property
    def language(self) -> Language:
        return Language.SWIFT

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix == ".swift"

    def parse_symbols(self, file_path: Path, content: bytes) -> list[SourceSymbol]:
        """Extract classes, structs, protocols, enums, extensions, functions, and properties."""
        root = self.parse_tree(content)
        symbols: list[SourceSymbol] = []

        self._extract_declarations(
            node=root,
            file_path=file_path,
            content=content,
            container_id=None,
            symbols=symbols,
        )
        return symbols

    def extract_dependencies(self, file_path: Path, content: bytes) -> list[DependencyEdge]:
        """Extract imports, protocol conformances, inheritance, and call sites."""
        root = self.parse_tree(content)
        edges: list[DependencyEdge] = []

        # 1. Imports
        for imp_node in self.find_descendants_of_type(root, "import_declaration"):
            imp_text = self.node_text(imp_node, content)
            clean_imp = imp_text.replace("import", "").strip()
            if clean_imp:
                edges.append(
                    DependencyEdge(
                        source_symbol_id=f"swift://{file_path.as_posix()}",
                        target_symbol_id=f"swift://{clean_imp}",
                        edge_kind=EdgeKind.IMPORTS,
                        location=self.node_location(imp_node, file_path),
                    )
                )

        # 2. Inheritance, conformances, and invocations
        self._extract_edges_from_ast(
            node=root,
            file_path=file_path,
            content=content,
            current_enclosing_id=f"swift://{file_path.as_posix()}",
            edges=edges,
        )
        return edges

    def _extract_declarations(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        container_id: str | None,
        symbols: list[SourceSymbol],
    ) -> None:
        """Recursively extract declared Swift symbols."""
        for child in node.children:
            if child.type == "protocol_declaration":
                symbol = self._parse_type_declaration(
                    child, file_path, content, container_id, SymbolKind.INTERFACE
                )
                if symbol:
                    symbols.append(symbol)
                    body = self._find_first_child(child, "protocol_body")
                    if body:
                        self._extract_declarations(
                            node=body,
                            file_path=file_path,
                            content=content,
                            container_id=symbol.id,
                            symbols=symbols,
                        )

            elif child.type == "class_declaration":
                kind = self._determine_class_decl_kind(child)
                symbol = self._parse_type_declaration(child, file_path, content, container_id, kind)
                if symbol:
                    symbols.append(symbol)
                    body = self._find_first_child(child, "class_body", "enum_class_body")
                    if body:
                        self._extract_declarations(
                            node=body,
                            file_path=file_path,
                            content=content,
                            container_id=symbol.id,
                            symbols=symbols,
                        )

            elif child.type in {"function_declaration", "init_declaration"}:
                symbol = self._parse_function(child, file_path, content, container_id)
                if symbol:
                    symbols.append(symbol)

            elif child.type == "property_declaration":
                symbol = self._parse_property(child, file_path, content, container_id)
                if symbol:
                    symbols.append(symbol)

            elif child.type == "ERROR":
                self._extract_from_error_node(
                    node=child,
                    file_path=file_path,
                    content=content,
                    container_id=container_id,
                    symbols=symbols,
                )

    def _extract_from_error_node(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        container_id: str | None,
        symbols: list[SourceSymbol],
    ) -> None:
        """Heuristically extract symbols embedded within Tree-sitter ERROR nodes."""
        kind_map = {
            "class": SymbolKind.CLASS,
            "struct": SymbolKind.STRUCT,
            "protocol": SymbolKind.INTERFACE,
            "enum": SymbolKind.ENUM,
            "extension": SymbolKind.CLASS,
        }
        children = node.children
        for i, c in enumerate(children):
            if c.type in kind_map and i + 1 < len(children):
                next_c = children[i + 1]
                if next_c.type in {"type_identifier", "simple_identifier", "identifier"}:
                    name = self.node_text(next_c, content)
                    kind = kind_map[c.type]
                    symbol_id = f"swift://{name}" if not container_id else f"{container_id}.{name}"
                    symbols.append(
                        SourceSymbol(
                            id=symbol_id,
                            name=name,
                            qualified_name=name,
                            kind=kind,
                            language=Language.SWIFT,
                            location=self.node_location(next_c, file_path),
                            visibility=Visibility.INTERNAL,
                            container_id=container_id,
                        )
                    )
            elif c.type == "ERROR":
                self._extract_from_error_node(
                    node=c,
                    file_path=file_path,
                    content=content,
                    container_id=container_id,
                    symbols=symbols,
                )

    def _determine_class_decl_kind(self, node: Node) -> SymbolKind:
        """Differentiate between struct, enum, class, and extension in Swift class_declaration."""
        child_types = [c.type for c in node.children]
        if "struct" in child_types:
            return SymbolKind.STRUCT
        elif "enum" in child_types or "enum_class_body" in child_types:
            return SymbolKind.ENUM
        elif "extension" in child_types:
            return SymbolKind.CLASS
        return SymbolKind.CLASS

    def _parse_type_declaration(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        container_id: str | None,
        kind: SymbolKind,
    ) -> SourceSymbol | None:
        """Parse class, struct, protocol, or enum declaration."""
        name_node = self._find_first_child(
            node, "type_identifier", "simple_identifier", "user_type"
        )
        if not name_node:
            return None

        name = self.node_text(name_node, content)
        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)

        symbol_id = f"swift://{name}" if not container_id else f"{container_id}.{name}"
        full_text = self.node_text(node, content)

        # Detect UI entry points: SwiftUI View or UIKit UIViewController / UIView
        is_ui = (
            ": View" in full_text
            or ": UIViewController" in full_text
            or ": UIView" in full_text
            or "some View" in full_text
        )
        is_test = name.endswith("Tests") or "XCTestCase" in full_text

        return SourceSymbol(
            id=symbol_id,
            name=name,
            qualified_name=name,
            kind=kind,
            language=Language.SWIFT,
            visibility=visibility,
            location=self.node_location(node, file_path),
            container_id=container_id,
            signature=self._extract_header_signature(node, content),
            annotations=annotations,
            is_entry_point=is_ui,
            is_test=is_test,
        )

    def _parse_function(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        container_id: str | None,
    ) -> SourceSymbol | None:
        """Parse function_declaration or init_declaration."""
        name_node = self._find_first_child(node, "simple_identifier", "type_identifier")
        if not name_node:
            if node.type == "init_declaration":
                name = "init"
            else:
                return None
        else:
            name = self.node_text(name_node, content)

        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)

        symbol_id = f"{container_id}#{name}" if container_id else f"swift://{name}"
        is_test = name.startswith("test")

        return SourceSymbol(
            id=symbol_id,
            name=name,
            qualified_name=name,
            kind=SymbolKind.METHOD if container_id else SymbolKind.FUNCTION,
            language=Language.SWIFT,
            visibility=visibility,
            location=self.node_location(node, file_path),
            container_id=container_id,
            signature=self._extract_header_signature(node, content),
            annotations=annotations,
            is_entry_point=False,
            is_test=is_test,
        )

    def _parse_property(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        container_id: str | None,
    ) -> SourceSymbol | None:
        """Parse property_declaration."""
        pattern_node = self._find_first_child(node, "pattern_binding")
        name_node = self._find_first_child(pattern_node or node, "simple_identifier", "identifier")
        if not name_node:
            return None

        name = self.node_text(name_node, content)
        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)

        symbol_id = f"{container_id}#{name}" if container_id else f"swift://{name}"

        return SourceSymbol(
            id=symbol_id,
            name=name,
            qualified_name=name,
            kind=SymbolKind.PROPERTY,
            language=Language.SWIFT,
            visibility=visibility,
            location=self.node_location(node, file_path),
            container_id=container_id,
            annotations=annotations,
        )

    def _extract_edges_from_ast(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        current_enclosing_id: str,
        edges: list[DependencyEdge],
    ) -> None:
        """Traverse AST to extract conformances, inheritance, and call expressions."""
        enclosing_id = current_enclosing_id

        if node.type in {"class_declaration", "protocol_declaration"}:
            name_node = self._find_first_child(
                node, "type_identifier", "simple_identifier", "user_type"
            )
            if name_node:
                name = self.node_text(name_node, content)
                enclosing_id = f"swift://{name}"

                # Extract inheritance and protocol conformances from inheritance_specifier
                for inh in self.find_descendants_of_type(node, "inheritance_specifier"):
                    inh_name = self.node_text(inh, content)
                    if inh_name and inh_name != name:
                        edges.append(
                            DependencyEdge(
                                source_symbol_id=enclosing_id,
                                target_symbol_id=f"swift://{inh_name}",
                                edge_kind=EdgeKind.IMPLEMENTS,
                                location=self.node_location(inh, file_path),
                            )
                        )

        elif node.type in {"function_declaration", "init_declaration"}:
            name_node = self._find_first_child(node, "simple_identifier")
            func_name = self.node_text(name_node, content) if name_node else "init"
            enclosing_id = f"{current_enclosing_id}#{func_name}"

        elif node.type == "property_declaration":
            for ann in self.find_descendants_of_type(node, "type_annotation"):
                for tid in self.find_descendants_of_type(ann, "type_identifier"):
                    tname = self.node_text(tid, content)
                    if tname:
                        edges.append(
                            DependencyEdge(
                                source_symbol_id=enclosing_id,
                                target_symbol_id=f"swift://{tname}",
                                edge_kind=EdgeKind.REFERENCES,
                                location=self.node_location(tid, file_path),
                            )
                        )

        elif node.type == "call_expression":
            callee_text = self._extract_call_target(node, content)
            if callee_text:
                edges.append(
                    DependencyEdge(
                        source_symbol_id=enclosing_id,
                        target_symbol_id=f"swift://{callee_text}",
                        edge_kind=EdgeKind.CALLS,
                        location=self.node_location(node, file_path),
                    )
                )

        for child in node.children:
            self._extract_edges_from_ast(
                node=child,
                file_path=file_path,
                content=content,
                current_enclosing_id=enclosing_id,
                edges=edges,
            )

    def _extract_call_target(self, call_node: Node, content: bytes) -> str | None:
        """Extract called function or method name from call_expression."""
        first_child = call_node.children[0] if call_node.children else None
        if not first_child:
            return None
        text = self.node_text(first_child, content)
        if "(" in text:
            text = text.split("(")[0]
        return text.strip() or None

    def _extract_modifiers(self, node: Node, content: bytes) -> tuple[list[str], list[str]]:
        """Extract modifiers and attributes/property wrappers."""
        modifiers: list[str] = []
        annotations: list[str] = []
        for c in node.children:
            if c.type == "modifiers":
                for mc in c.children:
                    if mc.type == "attribute":
                        annotations.append(self.node_text(mc, content))
                    else:
                        modifiers.append(self.node_text(mc, content))
            elif c.type == "attribute":
                annotations.append(self.node_text(c, content))
        return modifiers, annotations

    def _resolve_visibility(self, modifiers: list[str]) -> Visibility:
        """Resolve Swift access control level."""
        mapping = {
            "private": Visibility.PRIVATE,
            "fileprivate": Visibility.PRIVATE,
            "internal": Visibility.INTERNAL,
            "public": Visibility.PUBLIC,
            "open": Visibility.PUBLIC,
        }
        for m in modifiers:
            m_lower = m.lower()
            if m_lower in mapping:
                return mapping[m_lower]
        return Visibility.INTERNAL

    def _extract_header_signature(self, node: Node, content: bytes) -> str:
        """Extract header text before opening brace."""
        for c in node.children:
            if c.type in {"class_body", "protocol_body", "block"}:
                return (
                    content[node.start_byte : c.start_byte]
                    .decode("utf-8", errors="replace")
                    .strip()
                )
        return self.node_text(node, content)[:100]

    def _find_first_child(self, node: Node, *types: str) -> Node | None:
        """Return the first immediate child matching types."""
        for c in node.children:
            if c.type in types:
                return c
        return None
