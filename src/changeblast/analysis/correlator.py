"""Correlates Git diff line changes with AST declared symbols."""

from __future__ import annotations

from dataclasses import dataclass

from changeblast.adapters.graph.memory import InMemoryDependencyGraph
from changeblast.models.changeset import ChangedFile, ChangeSet
from changeblast.models.common import ChangeType
from changeblast.models.symbol import SourceSymbol


@dataclass(frozen=True)
class DirectlyModifiedSymbol:
    """A symbol whose AST declaration coordinates intersect with changed diff lines."""

    symbol: SourceSymbol
    changed_file: ChangedFile
    is_signature_modified: bool
    is_deleted: bool = False


class SymbolDiffCorrelator:
    """Intersects modified line ranges with AST symbols to pinpoint root changes."""

    def correlate(
        self,
        changeset: ChangeSet,
        graph: InMemoryDependencyGraph,
    ) -> list[DirectlyModifiedSymbol]:
        """Identify symbols directly modified or deleted in the changeset."""
        results: list[DirectlyModifiedSymbol] = []
        seen_ids: set[str] = set()

        for cf in changeset.changed_files:
            norm_path = cf.path.replace("\\", "/")

            if cf.change_type == ChangeType.DELETED:
                # File was deleted: all symbols previously declared in this file are deleted
                for sym in graph.get_symbols_in_file(norm_path):
                    if sym.id not in seen_ids:
                        seen_ids.add(sym.id)
                        results.append(
                            DirectlyModifiedSymbol(
                                symbol=sym,
                                changed_file=cf,
                                is_signature_modified=True,
                                is_deleted=True,
                            )
                        )
                continue

            # Modified or added file: intersect changed line ranges with symbol spans
            file_symbols = graph.get_symbols_in_file(norm_path)
            for sym in file_symbols:
                loc = sym.location
                is_hit = False
                is_sig = False

                for lr in cf.changed_line_ranges:
                    # Check if line range intersects symbol coordinates
                    if lr.end_line >= loc.start_line and lr.start_line <= loc.end_line:
                        is_hit = True
                        # If changed line touches the first line of the declaration, signature is modified
                        if lr.contains(loc.start_line):
                            is_sig = True
                        break

                if is_hit and sym.id not in seen_ids:
                    seen_ids.add(sym.id)
                    results.append(
                        DirectlyModifiedSymbol(
                            symbol=sym,
                            changed_file=cf,
                            is_signature_modified=is_sig,
                            is_deleted=False,
                        )
                    )

        return sorted(results, key=lambda item: item.symbol.id)
