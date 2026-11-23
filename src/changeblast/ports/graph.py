"""Dependency and call graph adapter port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from changeblast.models.edge import DependencyEdge
from changeblast.models.symbol import SourceSymbol


class IDependencyGraphAdapter(ABC):
    """Abstract interface for managing and traversing directed symbol dependency graphs."""

    @abstractmethod
    def add_symbol(self, symbol: SourceSymbol) -> None:
        """Register a symbol node in the graph."""
        ...

    @abstractmethod
    def add_edge(self, edge: DependencyEdge) -> None:
        """Register a directed relationship edge between symbols."""
        ...

    @abstractmethod
    def get_symbol(self, symbol_id: str) -> SourceSymbol | None:
        """Retrieve a symbol node by its unique deterministic ID."""
        ...

    @abstractmethod
    def get_direct_dependents(self, symbol_id: str) -> list[SourceSymbol]:
        """Find immediate upstream callers or subclasses that depend on the given symbol."""
        ...

    @abstractmethod
    def get_transitive_dependents(
        self,
        symbol_id: str,
        max_depth: int = 10,
    ) -> list[tuple[SourceSymbol, int, list[str]]]:
        """Traverse upstream dependents up to max_depth.

        Returns:
            List of tuples: (impacted_symbol, depth, propagation_path_symbol_ids).
        """
        ...

    @abstractmethod
    def detect_cycles(self) -> list[list[str]]:
        """Detect any circular dependency loops in the graph."""
        ...

    @property
    @abstractmethod
    def node_count(self) -> int:
        """Total number of registered symbol nodes."""
        ...

    @property
    @abstractmethod
    def edge_count(self) -> int:
        """Total number of registered dependency edges."""
        ...
