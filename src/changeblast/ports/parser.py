"""Language parser adapter port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from changeblast.models.common import Language
from changeblast.models.edge import DependencyEdge
from changeblast.models.symbol import SourceSymbol


class ILanguageParserAdapter(ABC):
    """Abstract interface for multi-language AST parsers (Kotlin, Java, Swift)."""

    @property
    @abstractmethod
    def language(self) -> Language:
        """The specific language supported by this parser adapter."""
        ...

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Determine whether this parser handles the given file based on extension or markers."""
        ...

    @abstractmethod
    def parse_symbols(self, file_path: Path, content: bytes) -> list[SourceSymbol]:
        """Extract all symbol declarations (classes, functions, properties) from source code.

        Args:
            file_path: Relative file path for location tracking.
            content: Raw UTF-8 bytes of source file.

        Returns:
            List of declared SourceSymbol entities.
        """
        ...

    @abstractmethod
    def extract_dependencies(self, file_path: Path, content: bytes) -> list[DependencyEdge]:
        """Extract all outgoing invocations, inheritance, and reference edges from source code.

        Args:
            file_path: Relative file path for location tracking.
            content: Raw UTF-8 bytes of source file.

        Returns:
            List of detected DependencyEdge instances.
        """
        ...
