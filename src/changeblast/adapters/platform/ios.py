"""iOS platform intelligence adapter."""

from __future__ import annotations

from pathlib import Path

from changeblast.adapters.parsers.swift import SwiftParserAdapter
from changeblast.models.common import Platform
from changeblast.models.edge import DependencyEdge
from changeblast.models.symbol import SourceSymbol


class IOSPlatformAdapter:
    """Coordinates parsing and platform intelligence for native iOS applications."""

    def __init__(self) -> None:
        self.swift_parser = SwiftParserAdapter()

    @property
    def platform(self) -> Platform:
        return Platform.IOS

    def can_handle(self, file_path: Path) -> bool:
        """Return True if file is a Swift source file."""
        return self.swift_parser.can_parse(file_path)

    def parse_file(self, file_path: Path, content: bytes) -> list[SourceSymbol]:
        """Extract symbols using the Swift language parser."""
        if self.swift_parser.can_parse(file_path):
            return self.swift_parser.parse_symbols(file_path, content)
        return []

    def extract_dependencies(self, file_path: Path, content: bytes) -> list[DependencyEdge]:
        """Extract dependency edges using the Swift language parser."""
        if self.swift_parser.can_parse(file_path):
            return self.swift_parser.extract_dependencies(file_path, content)
        return []
