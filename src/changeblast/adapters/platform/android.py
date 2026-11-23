"""Android platform intelligence adapter."""

from __future__ import annotations

from pathlib import Path

from changeblast.adapters.parsers.java import JavaParserAdapter
from changeblast.adapters.parsers.kotlin import KotlinParserAdapter
from changeblast.models.common import Platform
from changeblast.models.edge import DependencyEdge
from changeblast.models.symbol import SourceSymbol


class AndroidPlatformAdapter:
    """Coordinates parsing and platform intelligence for native Android applications."""

    def __init__(self) -> None:
        self.kotlin_parser = KotlinParserAdapter()
        self.java_parser = JavaParserAdapter()

    @property
    def platform(self) -> Platform:
        return Platform.ANDROID

    def can_handle(self, file_path: Path) -> bool:
        """Return True if file is a Kotlin or Java source file."""
        return self.kotlin_parser.can_parse(file_path) or self.java_parser.can_parse(file_path)

    def parse_file(self, file_path: Path, content: bytes) -> list[SourceSymbol]:
        """Extract symbols using the appropriate language parser."""
        if self.kotlin_parser.can_parse(file_path):
            return self.kotlin_parser.parse_symbols(file_path, content)
        elif self.java_parser.can_parse(file_path):
            return self.java_parser.parse_symbols(file_path, content)
        return []

    def extract_dependencies(self, file_path: Path, content: bytes) -> list[DependencyEdge]:
        """Extract dependency edges using the appropriate language parser."""
        if self.kotlin_parser.can_parse(file_path):
            return self.kotlin_parser.extract_dependencies(file_path, content)
        elif self.java_parser.can_parse(file_path):
            return self.java_parser.extract_dependencies(file_path, content)
        return []
