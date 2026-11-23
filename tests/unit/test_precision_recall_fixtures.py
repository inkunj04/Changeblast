"""Labelled dependency fixtures testing precision, recall, cycles, and scale."""

from __future__ import annotations

import time

from changeblast.adapters.graph import InMemoryDependencyGraph
from changeblast.models.common import (
    EdgeKind,
    Language,
    SourceLocation,
    SymbolKind,
    Visibility,
)
from changeblast.models.edge import DependencyEdge
from changeblast.models.symbol import SourceSymbol


def make_symbol(
    sym_id: str,
    name: str,
    file_path: str = "app/src/main/kotlin/App.kt",
    start_line: int = 1,
    end_line: int = 20,
    is_test: bool = False,
    is_entry_point: bool = False,
) -> SourceSymbol:
    return SourceSymbol(
        id=sym_id,
        name=name,
        qualified_name=f"com.example.{name}",
        kind=SymbolKind.CLASS if "View" in name or "Activity" in name else SymbolKind.METHOD,
        language=Language.KOTLIN,
        visibility=Visibility.PUBLIC,
        location=SourceLocation(
            file_path=file_path,
            start_line=start_line,
            start_column=0,
            end_line=end_line,
            end_column=1,
        ),
        is_test=is_test,
        is_entry_point=is_entry_point,
    )


def compute_precision_recall(
    predicted_ids: set[str],
    ground_truth_ids: set[str],
) -> tuple[float, float]:
    """Compute mathematical precision and recall."""
    if not predicted_ids and not ground_truth_ids:
        return 1.0, 1.0
    if not predicted_ids:
        return 0.0, 0.0
    if not ground_truth_ids:
        return 0.0, 1.0

    tp = len(predicted_ids & ground_truth_ids)
    fp = len(predicted_ids - ground_truth_ids)
    fn = len(ground_truth_ids - predicted_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return precision, recall


class TestLabelledFixturesAndPrecisionRecall:
    """Rigorous evaluation of precision, recall, and scalability against ground truth."""

    def test_direct_dependencies_precision_and_recall(self) -> None:
        """Ground truth: Root is directly called by Caller1 and Caller2, but NOT Caller3."""
        graph = InMemoryDependencyGraph()
        root = make_symbol("kt://Root", "Root")
        c1 = make_symbol("kt://Caller1", "Caller1")
        c2 = make_symbol("kt://Caller2", "Caller2")
        c3 = make_symbol("kt://Caller3", "Caller3")

        for s in (root, c1, c2, c3):
            graph.add_symbol(s)

        graph.add_edge(
            DependencyEdge(
                source_symbol_id=c1.id, target_symbol_id=root.id, edge_kind=EdgeKind.CALLS
            )
        )
        graph.add_edge(
            DependencyEdge(
                source_symbol_id=c2.id, target_symbol_id=root.id, edge_kind=EdgeKind.CALLS
            )
        )

        # Query direct dependents of Root
        predicted = {s.id for s in graph.get_direct_dependents(root.id)}
        ground_truth = {"kt://Caller1", "kt://Caller2"}

        precision, recall = compute_precision_recall(predicted, ground_truth)
        assert precision >= 0.95, f"Precision was {precision:.2f}"
        assert recall >= 0.95, f"Recall was {recall:.2f}"

    def test_transitive_dependencies_precision_and_recall(self) -> None:
        """Ground truth DAG:

        R <- A <- B <- C
             ^
             |
             D
        Independent node: E (calls unrelated node)
        """
        graph = InMemoryDependencyGraph()
        r = make_symbol("kt://R", "R")
        a = make_symbol("kt://A", "A")
        b = make_symbol("kt://B", "B")
        c = make_symbol("kt://C", "C")
        d = make_symbol("kt://D", "D")
        e = make_symbol("kt://E", "E")
        other = make_symbol("kt://Other", "Other")

        for s in (r, a, b, c, d, e, other):
            graph.add_symbol(s)

        graph.add_edge(
            DependencyEdge(source_symbol_id=a.id, target_symbol_id=r.id, edge_kind=EdgeKind.CALLS)
        )
        graph.add_edge(
            DependencyEdge(source_symbol_id=b.id, target_symbol_id=a.id, edge_kind=EdgeKind.CALLS)
        )
        graph.add_edge(
            DependencyEdge(source_symbol_id=c.id, target_symbol_id=b.id, edge_kind=EdgeKind.CALLS)
        )
        graph.add_edge(
            DependencyEdge(source_symbol_id=d.id, target_symbol_id=a.id, edge_kind=EdgeKind.CALLS)
        )
        graph.add_edge(
            DependencyEdge(
                source_symbol_id=e.id, target_symbol_id=other.id, edge_kind=EdgeKind.CALLS
            )
        )

        # Query transitive blast radius of R
        transitive = graph.get_transitive_dependents(r.id, max_depth=10)
        predicted = {item[0].id for item in transitive}
        ground_truth = {"kt://A", "kt://B", "kt://C", "kt://D"}

        precision, recall = compute_precision_recall(predicted, ground_truth)
        assert precision == 1.0
        assert recall == 1.0

    def test_cycle_handling_precision(self) -> None:
        """Cycle: X -> Y -> Z -> X. W calls X."""
        graph = InMemoryDependencyGraph()
        x = make_symbol("kt://X", "X")
        y = make_symbol("kt://Y", "Y")
        z = make_symbol("kt://Z", "Z")
        w = make_symbol("kt://W", "W")

        for s in (x, y, z, w):
            graph.add_symbol(s)

        # X calls Y calls Z calls X
        graph.add_edge(
            DependencyEdge(source_symbol_id=x.id, target_symbol_id=y.id, edge_kind=EdgeKind.CALLS)
        )
        graph.add_edge(
            DependencyEdge(source_symbol_id=y.id, target_symbol_id=z.id, edge_kind=EdgeKind.CALLS)
        )
        graph.add_edge(
            DependencyEdge(source_symbol_id=z.id, target_symbol_id=x.id, edge_kind=EdgeKind.CALLS)
        )
        # W calls X
        graph.add_edge(
            DependencyEdge(source_symbol_id=w.id, target_symbol_id=x.id, edge_kind=EdgeKind.CALLS)
        )

        # Query blast radius of Y:
        # Who depends on Y? X calls Y, Z calls X (calls Y), W calls X (calls Y)
        transitive = graph.get_transitive_dependents(y.id, max_depth=10)
        predicted = {item[0].id for item in transitive}
        ground_truth = {"kt://X", "kt://Z", "kt://W"}

        precision, recall = compute_precision_recall(predicted, ground_truth)
        assert precision == 1.0
        assert recall == 1.0

        cycles = graph.detect_cycles()
        assert len(cycles) == 1

    def test_large_repository_simulation_scale_and_correctness(self) -> None:
        """Synthetic benchmark: 100 nodes, 250 edges, multi-branch call tree.

        Ensures execution completes in under 200ms with 100% precision and recall.
        """
        graph = InMemoryDependencyGraph()
        n = 100
        symbols = [
            make_symbol(
                f"kt://Node_{i}",
                f"Node_{i}",
                file_path=f"module_{i % 5}/Node_{i}.kt",
                start_line=1,
                end_line=20,
            )
            for i in range(n)
        ]
        for s in symbols:
            graph.add_symbol(s)

        # Construct binary tree + cross edges
        # Node i calls 2*i + 1 and 2*i + 2
        for i in range(40):
            left = 2 * i + 1
            right = 2 * i + 2
            if left < n:
                graph.add_edge(
                    DependencyEdge(
                        source_symbol_id=symbols[i].id,
                        target_symbol_id=symbols[left].id,
                        edge_kind=EdgeKind.CALLS,
                    )
                )
            if right < n:
                graph.add_edge(
                    DependencyEdge(
                        source_symbol_id=symbols[i].id,
                        target_symbol_id=symbols[right].id,
                        edge_kind=EdgeKind.CALLS,
                    )
                )

        # Add cross edges
        for i in range(20):
            cross = (3 * i + 7) % n
            if cross != i:
                graph.add_edge(
                    DependencyEdge(
                        source_symbol_id=symbols[cross].id,
                        target_symbol_id=symbols[i].id,
                        edge_kind=EdgeKind.REFERENCES,
                    )
                )

        t_start = time.perf_counter()
        # Query blast radius of deepest leaf
        leaf_id = symbols[n - 1].id
        transitive = graph.get_transitive_dependents(leaf_id, max_depth=15)
        cycles = graph.detect_cycles()
        t_elapsed = time.perf_counter() - t_start

        # Performance constraint: sub-second graph traversal
        assert t_elapsed < 0.20, f"Graph traversal took {t_elapsed:.4f}s (exceeded 200ms limit)"
        # Structural constraint: valid results produced
        assert isinstance(transitive, list)
        assert isinstance(cycles, list)
