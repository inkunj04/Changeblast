"""Base utilities for Tree-sitter multi-language source parsers."""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language, Node, Parser

from changeblast.models.common import SourceLocation


class BaseTreeSitterParser:
    """Base parser wrapping Tree-sitter with resilience to malformed syntax."""

    def __init__(self, language: Language) -> None:
        self._language = language
        self._parser = Parser(language)

    def parse_tree(self, content: bytes) -> Node:
        """Parse source bytes into a concrete syntax tree root node.

        Tree-sitter guarantees an AST is produced even if code contains syntax errors.
        """
        tree = self._parser.parse(content)
        return tree.root_node

    @staticmethod
    def node_location(node: Node, file_path: Path | str) -> SourceLocation:
        """Translate Tree-sitter 0-based row coordinates to 1-based SourceLocation."""
        clean_path = str(file_path).replace("\\", "/")
        return SourceLocation(
            file_path=clean_path,
            start_line=node.start_point.row + 1,
            start_column=node.start_point.column,
            end_line=node.end_point.row + 1,
            end_column=node.end_point.column,
        )

    @staticmethod
    def node_text(node: Node, content: bytes | None = None) -> str:
        """Decode raw text of a syntax node safely as UTF-8."""
        raw = content[node.start_byte : node.end_byte] if content is not None else node.text or b""
        return raw.decode("utf-8", errors="replace").strip()

    @staticmethod
    def extract_snippet(node: Node, max_lines: int = 5) -> str:
        """Extract a short, sanitized snippet for evidence references."""
        text = (node.text or b"").decode("utf-8", errors="replace").strip()
        lines = text.splitlines()
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + "\n..."
        return "\n".join(lines)

    @staticmethod
    def find_children_of_type(node: Node, *types: str) -> list[Node]:
        """Find immediate children matching any of the specified type strings."""
        return [c for c in node.children if c.type in types]

    @staticmethod
    def find_descendants_of_type(node: Node, *types: str) -> list[Node]:
        """Recursively find all descendant nodes matching any of the specified types."""
        matched: list[Node] = []

        def _traverse(curr: Node) -> None:
            if curr.type in types:
                matched.append(curr)
            for child in curr.children:
                _traverse(child)

        _traverse(node)
        return matched
