"""Kotlin Tree-sitter parser adapter."""

from __future__ import annotations

from pathlib import Path

import tree_sitter_kotlin as tskotlin
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


class KotlinParserAdapter(BaseTreeSitterParser, ILanguageParserAdapter):
    """Parses Kotlin source files into unified SourceSymbol and DependencyEdge models."""

    def __init__(self) -> None:
        super().__init__(TsLanguage(tskotlin.language()))

    @property
    def language(self) -> Language:
        return Language.KOTLIN

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix in {".kt", ".kts"}

    def parse_symbols(self, file_path: Path, content: bytes) -> list[SourceSymbol]:
        """Extract classes, interfaces, objects, functions, and properties."""
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
        """Extract imports, supertypes (inheritance/implementation), and call expressions."""
        root = self.parse_tree(content)
        pkg_name = self._extract_package(root, content)
        edges: list[DependencyEdge] = []

        # 1. Imports
        for imp_node in self.find_descendants_of_type(root, "import_header", "import"):
            imp_text = self.node_text(imp_node, content)
            clean_imp = imp_text.replace("import", "").strip()
            if clean_imp:
                edges.append(
                    DependencyEdge(
                        source_symbol_id=f"kt://{file_path.as_posix()}",
                        target_symbol_id=f"kt://{clean_imp}",
                        edge_kind=EdgeKind.IMPORTS,
                        location=self.node_location(imp_node, file_path),
                    )
                )

        # 2. Inheritance and call sites
        self._extract_edges_from_ast(
            node=root,
            file_path=file_path,
            content=content,
            pkg_name=pkg_name,
            current_enclosing_id=f"kt://{file_path.as_posix()}",
            edges=edges,
        )
        return edges

    def _extract_package(self, root: Node, content: bytes) -> str:
        """Extract package identifier from package_header."""
        for child in root.children:
            if child.type == "package_header":
                text = self.node_text(child, content)
                return text.replace("package", "").strip()
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
        """Recursively extract declared symbols from syntax tree."""
        for child in node.children:
            if child.type in {"class_declaration", "object_declaration"}:
                symbol = self._parse_class_or_object(
                    child, file_path, content, pkg_name, container_id
                )
                if symbol:
                    symbols.append(symbol)
                    # Inspect class body for members
                    body = self._find_body(child)
                    if body:
                        self._extract_declarations(
                            node=body,
                            file_path=file_path,
                            content=content,
                            pkg_name=pkg_name,
                            container_id=symbol.id,
                            symbols=symbols,
                        )
            elif child.type == "function_declaration":
                symbol = self._parse_function(child, file_path, content, pkg_name, container_id)
                if symbol:
                    symbols.append(symbol)
            elif child.type == "property_declaration":
                symbol = self._parse_property(child, file_path, content, pkg_name, container_id)
                if symbol:
                    symbols.append(symbol)
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
        children = node.children
        for i, c in enumerate(children):
            if c.type in {"class", "interface", "object"} and i + 1 < len(children):
                next_c = children[i + 1]
                if next_c.type in {"identifier", "simple_identifier"}:
                    name = self.node_text(next_c, content)
                    kind = SymbolKind.INTERFACE if c.type == "interface" else SymbolKind.CLASS
                    qualified_name = f"{pkg_name}.{name}" if pkg_name else name
                    symbol_id = (
                        f"kt://{qualified_name}" if not container_id else f"{container_id}.{name}"
                    )
                    symbols.append(
                        SourceSymbol(
                            id=symbol_id,
                            name=name,
                            qualified_name=qualified_name,
                            kind=kind,
                            language=Language.KOTLIN,
                            location=self.node_location(next_c, file_path),
                            visibility=Visibility.PUBLIC,
                            container_id=container_id,
                        )
                    )
            elif c.type == "fun" and i + 1 < len(children):
                next_c = children[i + 1]
                if next_c.type in {"identifier", "simple_identifier"}:
                    name = self.node_text(next_c, content)
                    qualified_name = f"{pkg_name}.{name}" if pkg_name else name
                    symbol_id = (
                        f"kt://{qualified_name}" if not container_id else f"{container_id}#{name}"
                    )
                    symbols.append(
                        SourceSymbol(
                            id=symbol_id,
                            name=name,
                            qualified_name=qualified_name,
                            kind=SymbolKind.FUNCTION if not container_id else SymbolKind.METHOD,
                            language=Language.KOTLIN,
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

    def _find_body(self, node: Node) -> Node | None:
        """Find the body block of a class or function."""
        for c in node.children:
            if c.type in {"class_body", "enum_class_body", "function_body", "block"}:
                return c
        return None

    def _parse_class_or_object(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        container_id: str | None,
    ) -> SourceSymbol | None:
        """Parse class_declaration or object_declaration into SourceSymbol."""
        name_node = self._find_first_child(node, "identifier", "simple_identifier")
        if not name_node:
            return None

        name = self.node_text(name_node, content)
        child_types = [c.type for c in node.children]

        # Determine SymbolKind
        if "interface" in child_types:
            kind = SymbolKind.INTERFACE
        elif "enum_class_body" in child_types:
            kind = SymbolKind.ENUM
        else:
            kind = SymbolKind.CLASS

        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)

        qualified_name = f"{pkg_name}.{name}" if pkg_name else name
        symbol_id = f"kt://{qualified_name}" if not container_id else f"{container_id}.{name}"

        # Heuristic checks
        full_text = self.node_text(node, content)
        is_entry_point = any(
            marker in full_text for marker in ["Activity", "Fragment", "ComposeScreen"]
        ) or any("Composable" in a for a in annotations)
        is_test = name.endswith("Test") or any("Test" in a for a in annotations)

        return SourceSymbol(
            id=symbol_id,
            name=name,
            qualified_name=qualified_name,
            kind=kind,
            language=Language.KOTLIN,
            visibility=visibility,
            location=self.node_location(node, file_path),
            container_id=container_id,
            signature=self._extract_class_signature(node, content),
            annotations=annotations,
            is_entry_point=is_entry_point,
            is_test=is_test,
        )

    def _parse_function(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        container_id: str | None,
    ) -> SourceSymbol | None:
        """Parse function_declaration into SourceSymbol."""
        name_node = self._find_first_child(node, "identifier", "simple_identifier")
        if not name_node:
            return None

        name = self.node_text(name_node, content)
        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)

        is_composable = any("Composable" in a for a in annotations)
        is_test = any("Test" in a for a in annotations) or name.startswith("test")

        if container_id:
            symbol_id = f"{container_id}#{name}"
            qualified_name = f"{container_id.replace('kt://', '')}.{name}"
            kind = SymbolKind.METHOD
        else:
            qualified_name = f"{pkg_name}.{name}" if pkg_name else name
            symbol_id = f"kt://{qualified_name}"
            kind = SymbolKind.FUNCTION

        signature = self._extract_func_signature(node, content)

        return SourceSymbol(
            id=symbol_id,
            name=name,
            qualified_name=qualified_name,
            kind=kind,
            language=Language.KOTLIN,
            visibility=visibility,
            location=self.node_location(node, file_path),
            container_id=container_id,
            signature=signature,
            annotations=annotations,
            is_entry_point=is_composable,
            is_test=is_test,
        )

    def _parse_property(
        self,
        node: Node,
        file_path: Path,
        content: bytes,
        pkg_name: str,
        container_id: str | None,
    ) -> SourceSymbol | None:
        """Parse property_declaration into SourceSymbol."""
        var_decl = self._find_first_child(node, "variable_declaration")
        name_node = self._find_first_child(var_decl or node, "identifier", "simple_identifier")
        if not name_node:
            return None

        name = self.node_text(name_node, content)
        modifiers, annotations = self._extract_modifiers(node, content)
        visibility = self._resolve_visibility(modifiers)

        if container_id:
            symbol_id = f"{container_id}#{name}"
            qualified_name = f"{container_id.replace('kt://', '')}.{name}"
        else:
            qualified_name = f"{pkg_name}.{name}" if pkg_name else name
            symbol_id = f"kt://{qualified_name}"

        return SourceSymbol(
            id=symbol_id,
            name=name,
            qualified_name=qualified_name,
            kind=SymbolKind.PROPERTY,
            language=Language.KOTLIN,
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
        pkg_name: str,
        current_enclosing_id: str,
        edges: list[DependencyEdge],
    ) -> None:
        """Traverse AST to extract inheritance, implementations, and call expressions."""
        enclosing_id = current_enclosing_id

        if node.type in {"class_declaration", "object_declaration"}:
            name_node = self._find_first_child(node, "identifier", "simple_identifier")
            if name_node:
                name = self.node_text(name_node, content)
                enclosing_id = f"kt://{pkg_name}.{name}" if pkg_name else f"kt://{name}"

                # Extract supertypes from delegation_specifiers
                for spec in self.find_descendants_of_type(
                    node, "delegation_specifiers", "delegation_specifier"
                ):
                    for super_type in self.find_descendants_of_type(
                        spec, "user_type", "identifier", "simple_identifier"
                    ):
                        super_name = self.node_text(super_type, content)
                        if super_name and super_name not in {name, "super"}:
                            edges.append(
                                DependencyEdge(
                                    source_symbol_id=enclosing_id,
                                    target_symbol_id=f"kt://{super_name}",
                                    edge_kind=EdgeKind.EXTENDS,
                                    location=self.node_location(super_type, file_path),
                                )
                            )

        elif node.type == "function_declaration":
            name_node = self._find_first_child(node, "identifier", "simple_identifier")
            if name_node:
                func_name = self.node_text(name_node, content)
                enclosing_id = f"{current_enclosing_id}#{func_name}"

        elif node.type == "call_expression":
            callee_text = self._extract_call_target(node, content)
            if callee_text:
                edges.append(
                    DependencyEdge(
                        source_symbol_id=enclosing_id,
                        target_symbol_id=f"kt://{callee_text}",
                        edge_kind=EdgeKind.CALLS,
                        location=self.node_location(node, file_path),
                    )
                )

        # Recurse through children
        for child in node.children:
            self._extract_edges_from_ast(
                node=child,
                file_path=file_path,
                content=content,
                pkg_name=pkg_name,
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
        """Extract visibility modifiers and annotations."""
        modifiers: list[str] = []
        annotations: list[str] = []
        for c in node.children:
            if c.type == "modifiers":
                for mc in c.children:
                    if mc.type == "annotation":
                        annotations.append(self.node_text(mc, content))
                    elif mc.type in {"visibility_modifier", "inheritance_modifier"}:
                        modifiers.append(self.node_text(mc, content))
            elif c.type == "annotation":
                annotations.append(self.node_text(c, content))
        return modifiers, annotations

    def _resolve_visibility(self, modifiers: list[str]) -> Visibility:
        """Map extracted modifier tokens to domain Visibility enum."""
        mapping = {
            "private": Visibility.PRIVATE,
            "protected": Visibility.PROTECTED,
            "internal": Visibility.INTERNAL,
            "public": Visibility.PUBLIC,
        }
        for m in modifiers:
            m_lower = m.lower()
            if m_lower in mapping:
                return mapping[m_lower]
        return Visibility.PUBLIC

    def _extract_class_signature(self, node: Node, content: bytes) -> str:
        """Extract header signature up to class body."""
        for c in node.children:
            if c.type in {"class_body", "enum_class_body"}:
                return (
                    content[node.start_byte : c.start_byte]
                    .decode("utf-8", errors="replace")
                    .strip()
                )
        return self.node_text(node, content)[:100]

    def _extract_func_signature(self, node: Node, content: bytes) -> str:
        """Extract function signature up to body."""
        for c in node.children:
            if c.type in {"function_body", "block"}:
                return (
                    content[node.start_byte : c.start_byte]
                    .decode("utf-8", errors="replace")
                    .strip()
                )
        return self.node_text(node, content)[:100]

    def _find_first_child(self, node: Node, *types: str) -> Node | None:
        """Return the first immediate child matching any of the specified types."""
        for c in node.children:
            if c.type in types:
                return c
        return None
