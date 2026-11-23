"""Java Tree-sitter parser adapter."""

from __future__ import annotations

from pathlib import Path

import tree_sitter_java as tsjava
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


class JavaParserAdapter(BaseTreeSitterParser, ILanguageParserAdapter):
    """Parses Java source files into unified SourceSymbol and DependencyEdge models."""

    def __init__(self) -> None:
        super().__init__(TsLanguage(tsjava.language()))

    @property
    def language(self) -> Language:
        return Language.JAVA

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix == ".java"

    def parse_symbols(self, file_path: Path, content: bytes) -> list[SourceSymbol]:
        """Extract classes, interfaces, records, enums, methods, and fields."""
        root = self.parse_tree(content)
        pkg_name = self._extract_package(root, content)
        symbols: list[SourceSymbol] = []

        self._extract_declarations(
            node=root,
            file_path=file_path,
            content=content,
            pkg_name=pkg_name,
            container_id=None,
            symbols=symbols,
        )
        return symbols

    def extract_dependencies(self, file_path: Path, content: bytes) -> list[DependencyEdge]:
        """Extract imports, inheritance, interfaces, and method call invocations."""
        root = self.parse_tree(content)
        pkg_name = self._extract_package(root, content)
        edges: list[DependencyEdge] = []

        # 1. Imports
        for imp_node in self.find_descendants_of_type(root, "import_declaration"):
            imp_text = self.node_text(imp_node, content)
            clean_imp = imp_text.replace("import", "").replace("static", "").rstrip(";").strip()
            if clean_imp:
                edges.append(
                    DependencyEdge(
                        source_symbol_id=f"java://{file_path.as_posix()}",
                        target_symbol_id=f"java://{clean_imp}",
                        edge_kind=EdgeKind.IMPORTS,
                        location=self.node_location(imp_node, file_path),
                    )
                )

        # 2. Inheritance, implementation, and invocations
        self._extract_edges_from_ast(
            node=root,
            file_path=file_path,
            content=content,
            pkg_name=pkg_name,
            current_enclosing_id=f"java://{file_path.as_posix()}",
            edges=edges,
        )
        return edges

    def _extract_package(self, root: Node, content: bytes) -> str:
        """Extract package identifier from package_declaration."""
        for child in root.children:
            if child.type == "package_declaration":
                text = self.node_text(child, content)
                return text.replace("package", "").rstrip(";").strip()
        return ""

    def _extract_declarations(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        container_id: str | None,
        symbols: list[SourceSymbol],
    ) -> None:
        """Recursively extract declared types and members from Java AST."""
        type_declaration_kinds = {
            "class_declaration": SymbolKind.CLASS,
            "interface_declaration": SymbolKind.INTERFACE,
            "record_declaration": SymbolKind.STRUCT,
            "enum_declaration": SymbolKind.ENUM,
        }

        for child in node.children:
            if child.type in type_declaration_kinds:
                kind = type_declaration_kinds[child.type]
                symbol = self._parse_type_declaration(
                    child, file_path, content, pkg_name, container_id, kind
                )
                if symbol:
                    symbols.append(symbol)
                    body = self._find_first_child(
                        child, "class_body", "interface_body", "enum_body"
                    )
                    if body:
                        self._extract_declarations(
                            node=body,
                            file_path=file_path,
                            content=content,
                            pkg_name=pkg_name,
                            container_id=symbol.id,
                            symbols=symbols,
                        )
            elif child.type in {"method_declaration", "constructor_declaration"}:
                symbol = self._parse_method(child, file_path, content, pkg_name, container_id)
                if symbol:
                    symbols.append(symbol)
            elif child.type == "field_declaration":
                field_symbols = self._parse_fields(
                    child, file_path, content, pkg_name, container_id
                )
                symbols.extend(field_symbols)
            elif child.type == "ERROR":
                self._extract_from_error_node(
                    node=child,
                    file_path=file_path,
                    content=content,
                    pkg_name=pkg_name,
                    container_id=container_id,
                    symbols=symbols,
                )

    def _extract_from_error_node(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        container_id: str | None,
        symbols: list[SourceSymbol],
    ) -> None:
        """Heuristically extract symbols embedded within Tree-sitter ERROR nodes."""
        kind_map = {
            "class": SymbolKind.CLASS,
            "interface": SymbolKind.INTERFACE,
            "record": SymbolKind.STRUCT,
            "enum": SymbolKind.ENUM,
        }
        children = node.children
        for i, c in enumerate(children):
            if c.type in kind_map and i + 1 < len(children):
                next_c = children[i + 1]
                if next_c.type == "identifier":
                    name = self.node_text(next_c, content)
                    kind = kind_map[c.type]
                    qualified_name = f"{pkg_name}.{name}" if pkg_name else name
                    symbol_id = (
                        f"java://{qualified_name}" if not container_id else f"{container_id}.{name}"
                    )
                    symbols.append(
                        SourceSymbol(
                            id=symbol_id,
                            name=name,
                            qualified_name=qualified_name,
                            kind=kind,
                            language=Language.JAVA,
                            location=self.node_location(next_c, file_path),
                            visibility=Visibility.PUBLIC,
                            container_id=container_id,
                        )
                    )
            elif c.type == "ERROR":
                self._extract_from_error_node(
                    node=c,
                    file_path=file_path,
                    content=content,
                    pkg_name=pkg_name,
                    container_id=container_id,
                    symbols=symbols,
                )

    def _parse_type_declaration(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        container_id: str | None,
        kind: SymbolKind,
    ) -> SourceSymbol | None:
        """Parse class, interface, enum, or record declaration."""
        name_node = self._find_first_child(node, "identifier")
        if not name_node:
            return None

        name = self.node_text(name_node, content)
        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)

        qualified_name = f"{pkg_name}.{name}" if pkg_name else name
        symbol_id = f"java://{qualified_name}" if not container_id else f"{container_id}.{name}"

        full_text = self.node_text(node, content)
        is_entry_point = any(
            marker in full_text
            for marker in ["Activity", "Fragment", "Service", "BroadcastReceiver"]
        )
        is_test = name.endswith("Test") or any("Test" in a for a in annotations)

        return SourceSymbol(
            id=symbol_id,
            name=name,
            qualified_name=qualified_name,
            kind=kind,
            language=Language.JAVA,
            visibility=visibility,
            location=self.node_location(node, file_path),
            container_id=container_id,
            signature=self._extract_header_signature(node, content),
            annotations=annotations,
            is_entry_point=is_entry_point,
            is_test=is_test,
        )

    def _parse_method(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        container_id: str | None,
    ) -> SourceSymbol | None:
        """Parse method_declaration or constructor_declaration."""
        name_node = self._find_first_child(node, "identifier")
        if not name_node:
            return None

        name = self.node_text(name_node, content)
        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)

        if container_id:
            symbol_id = f"{container_id}#{name}"
            qualified_name = f"{container_id.replace('java://', '')}.{name}"
        else:
            qualified_name = f"{pkg_name}.{name}" if pkg_name else name
            symbol_id = f"java://{qualified_name}"

        is_test = any("Test" in a for a in annotations) or name.startswith("test")

        return SourceSymbol(
            id=symbol_id,
            name=name,
            qualified_name=qualified_name,
            kind=SymbolKind.METHOD,
            language=Language.JAVA,
            visibility=visibility,
            location=self.node_location(node, file_path),
            container_id=container_id,
            signature=self._extract_header_signature(node, content),
            annotations=annotations,
            is_entry_point=False,
            is_test=is_test,
        )

    def _parse_fields(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        container_id: str | None,
    ) -> list[SourceSymbol]:
        """Parse field_declaration (can define multiple declarators)."""
        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)
        symbols: list[SourceSymbol] = []

        for decl in self.find_children_of_type(node, "variable_declarator"):
            name_node = self._find_first_child(decl, "identifier")
            if name_node:
                name = self.node_text(name_node, content)
                symbol_id = (
                    f"{container_id}#{name}" if container_id else f"java://{pkg_name}.{name}"
                )
                symbols.append(
                    SourceSymbol(
                        id=symbol_id,
                        name=name,
                        qualified_name=symbol_id.replace("java://", "").replace("#", "."),
                        kind=SymbolKind.PROPERTY,
                        language=Language.JAVA,
                        visibility=visibility,
                        location=self.node_location(decl, file_path),
                        container_id=container_id,
                        annotations=annotations,
                    )
                )
        return symbols

    def _extract_edges_from_ast(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        current_enclosing_id: str,
        edges: list[DependencyEdge],
    ) -> None:
        """Traverse AST to extract inheritance, implementations, and call sites."""
        enclosing_id = current_enclosing_id

        if node.type in {"class_declaration", "interface_declaration", "record_declaration"}:
            name_node = self._find_first_child(node, "identifier")
            if name_node:
                name = self.node_text(name_node, content)
                enclosing_id = f"java://{pkg_name}.{name}" if pkg_name else f"java://{name}"

                # 1. Superclass: extends Foo
                superclass = self._find_first_child(node, "superclass")
                if superclass:
                    super_type = self._find_first_child(superclass, "type_identifier")
                    if super_type:
                        super_name = self.node_text(super_type, content)
                        edges.append(
                            DependencyEdge(
                                source_symbol_id=enclosing_id,
                                target_symbol_id=f"java://{super_name}",
                                edge_kind=EdgeKind.EXTENDS,
                                location=self.node_location(super_type, file_path),
                            )
                        )

                # 2. Interfaces: implements Bar, Baz
                interfaces = self._find_first_child(node, "super_interfaces", "extends_interfaces")
                if interfaces:
                    for iface in self.find_descendants_of_type(interfaces, "type_identifier"):
                        iface_name = self.node_text(iface, content)
                        edges.append(
                            DependencyEdge(
                                source_symbol_id=enclosing_id,
                                target_symbol_id=f"java://{iface_name}",
                                edge_kind=EdgeKind.IMPLEMENTS,
                                location=self.node_location(iface, file_path),
                            )
                        )

        elif node.type in {"method_declaration", "constructor_declaration"}:
            name_node = self._find_first_child(node, "identifier")
            if name_node:
                name = self.node_text(name_node, content)
                enclosing_id = f"{current_enclosing_id}#{name}"

        elif node.type == "method_invocation":
            # Extract target method name (prefer 'name' field in method_invocation)
            name_node = node.child_by_field_name("name") or self._find_first_child(
                node, "identifier"
            )
            if name_node:
                method_name = self.node_text(name_node, content)
                edges.append(
                    DependencyEdge(
                        source_symbol_id=enclosing_id,
                        target_symbol_id=f"java://{method_name}",
                        edge_kind=EdgeKind.CALLS,
                        location=self.node_location(node, file_path),
                    )
                )

        elif node.type == "object_creation_expression":
            type_node = self._find_first_child(node, "type_identifier")
            if type_node:
                inst_name = self.node_text(type_node, content)
                edges.append(
                    DependencyEdge(
                        source_symbol_id=enclosing_id,
                        target_symbol_id=f"java://{inst_name}",
                        edge_kind=EdgeKind.INSTANTIATES,
                        location=self.node_location(node, file_path),
                    )
                )

        for child in node.children:
            self._extract_edges_from_ast(
                node=child,
                file_path=file_path,
                content=content,
                pkg_name=pkg_name,
                current_enclosing_id=enclosing_id,
                edges=edges,
            )

    def _extract_modifiers(self, node: Node, content: bytes) -> tuple[list[str], list[str]]:
        """Extract modifiers and annotations from node."""
        modifiers: list[str] = []
        annotations: list[str] = []
        for c in node.children:
            if c.type == "modifiers":
                for mc in c.children:
                    if "annotation" in mc.type:
                        annotations.append(self.node_text(mc, content))
                    else:
                        modifiers.append(self.node_text(mc, content))
            elif "annotation" in c.type:
                annotations.append(self.node_text(c, content))
        return modifiers, annotations

    def _resolve_visibility(self, modifiers: list[str]) -> Visibility:
        """Resolve access control visibility."""
        mapping = {
            "private": Visibility.PRIVATE,
            "protected": Visibility.PROTECTED,
            "public": Visibility.PUBLIC,
        }
        for m in modifiers:
            m_lower = m.lower()
            if m_lower in mapping:
                return mapping[m_lower]
        return Visibility.PACKAGE_PRIVATE

    def _extract_header_signature(self, node: Node, content: bytes) -> str:
        """Extract header text before opening brace."""
        for c in node.children:
            if c.type in {"class_body", "interface_body", "enum_body", "block"}:
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
