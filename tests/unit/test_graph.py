"""Unit tests for InMemoryDependencyGraph implementation."""

from __future__ import annotations

from changeblast.adapters.graph import InMemoryDependencyGraph
from changeblast.models.common import (
    ConfidenceLevel,
    EdgeKind,
    EvidenceType,
    Language,
    SourceLocation,
    SymbolKind,
    Visibility,
)
from changeblast.models.edge import DependencyEdge
from changeblast.models.evidence import EvidenceReference
from changeblast.models.symbol import SourceSymbol


def make_symbol(
    symbol_id: str,
    name: str,
    file_path: str = "app/src/main/kotlin/App.kt",
    start_line: int = 10,
    end_line: int = 20,
    kind: SymbolKind = SymbolKind.CLASS,
    is_test: bool = False,
    is_entry_point: bool = False,
) -> SourceSymbol:
    return SourceSymbol(
        id=symbol_id,
        name=name,
        qualified_name=f"com.example.{name}",
        kind=kind,
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


class TestInMemoryDependencyGraph:
    """Validate in-memory graph operations, traversals, cycle detection, and queries."""

    def test_add_and_retrieve_symbols_and_edges(self) -> None:
        graph = InMemoryDependencyGraph()
        s1 = make_symbol("kt://A", "A")
        s2 = make_symbol("kt://B", "B")

        graph.add_symbol(s1)
        graph.add_symbol(s2)

        edge = DependencyEdge(
            source_symbol_id=s1.id,
            target_symbol_id=s2.id,
            edge_kind=EdgeKind.CALLS,
            confidence=ConfidenceLevel.VERIFIED,
        )
        graph.add_edge(edge)

        assert graph.node_count == 2
        assert graph.edge_count == 1
        assert graph.get_symbol("kt://A") == s1
        assert graph.get_symbol("kt://NonExistent") is None

    def test_direct_and_transitive_dependents_blast_radius(self) -> None:
        # A -> B -> C (A calls B, B calls C)
        # Blast radius of C: B (depth 1), A (depth 2)
        graph = InMemoryDependencyGraph()
        sa = make_symbol("kt://A", "A")
        sb = make_symbol("kt://B", "B")
        sc = make_symbol("kt://C", "C")

        for s in (sa, sb, sc):
            graph.add_symbol(s)

        # A calls B
        graph.add_edge(
            DependencyEdge(
                source_symbol_id=sa.id,
                target_symbol_id=sb.id,
                edge_kind=EdgeKind.CALLS,
            )
        )
        # B calls C
        graph.add_edge(
            DependencyEdge(
                source_symbol_id=sb.id,
                target_symbol_id=sc.id,
                edge_kind=EdgeKind.CALLS,
            )
        )

        direct_dependents = graph.get_direct_dependents(sc.id)
        assert len(direct_dependents) == 1
        assert direct_dependents[0].id == sb.id

        transitive = graph.get_transitive_dependents(sc.id, max_depth=5)
        assert len(transitive) == 2
        assert transitive[0][0].id == sb.id
        assert transitive[0][1] == 1
        assert transitive[0][2] == [sc.id, sb.id]

        assert transitive[1][0].id == sa.id
        assert transitive[1][1] == 2
        assert transitive[1][2] == [sc.id, sb.id, sa.id]

    def test_forward_direct_and_transitive_dependencies(self) -> None:
        # A calls B, B calls C
        graph = InMemoryDependencyGraph()
        sa = make_symbol("kt://A", "A")
        sb = make_symbol("kt://B", "B")
        sc = make_symbol("kt://C", "C")
        for s in (sa, sb, sc):
            graph.add_symbol(s)

        graph.add_edge(
            DependencyEdge(
                source_symbol_id=sa.id,
                target_symbol_id=sb.id,
                edge_kind=EdgeKind.CALLS,
            )
        )
        graph.add_edge(
            DependencyEdge(
                source_symbol_id=sb.id,
                target_symbol_id=sc.id,
                edge_kind=EdgeKind.CALLS,
            )
        )

        direct = graph.get_direct_dependencies(sa.id)
        assert len(direct) == 1
        assert direct[0].id == sb.id

        transitive = graph.get_transitive_dependencies(sa.id, max_depth=5)
        assert len(transitive) == 2
        assert transitive[0][0].id == sb.id
        assert transitive[0][1] == 1
        assert transitive[1][0].id == sc.id
        assert transitive[1][1] == 2

    def test_max_depth_limiting(self) -> None:
        # Chain: S0 -> S1 -> S2 -> S3 -> S4
        graph = InMemoryDependencyGraph()
        symbols = [make_symbol(f"kt://S{i}", f"S{i}") for i in range(5)]
        for s in symbols:
            graph.add_symbol(s)

        for i in range(4):
            graph.add_edge(
                DependencyEdge(
                    source_symbol_id=symbols[i].id,
                    target_symbol_id=symbols[i + 1].id,
                    edge_kind=EdgeKind.CALLS,
                )
            )

        # Query blast radius of S4 with depth limit 2
        res = graph.get_transitive_dependents("kt://S4", max_depth=2)
        assert len(res) == 2
        depths = [item[1] for item in res]
        assert depths == [1, 2]
        sym_names = [item[0].name for item in res]
        assert sym_names == ["S3", "S2"]

    def test_cycle_detection_and_safe_traversal(self) -> None:
        # A -> B -> C -> A (Circular loop)
        graph = InMemoryDependencyGraph()
        sa = make_symbol("kt://A", "A")
        sb = make_symbol("kt://B", "B")
        sc = make_symbol("kt://C", "C")

        for s in (sa, sb, sc):
            graph.add_symbol(s)

        graph.add_edge(
            DependencyEdge(source_symbol_id=sa.id, target_symbol_id=sb.id, edge_kind=EdgeKind.CALLS)
        )
        graph.add_edge(
            DependencyEdge(source_symbol_id=sb.id, target_symbol_id=sc.id, edge_kind=EdgeKind.CALLS)
        )
        graph.add_edge(
            DependencyEdge(source_symbol_id=sc.id, target_symbol_id=sa.id, edge_kind=EdgeKind.CALLS)
        )

        cycles = graph.detect_cycles()
        assert len(cycles) == 1
        assert len(cycles[0]) == 4  # e.g. [A, B, C, A]
        assert cycles[0][0] == cycles[0][-1]

        # Ensure transitive traversal terminates cleanly without infinite recursion
        transitive = graph.get_transitive_dependents(sc.id, max_depth=10)
        assert len(transitive) == 2
        target_ids = {item[0].id for item in transitive}
        assert target_ids == {sa.id, sb.id}

    def test_confidence_and_evidence_propagation(self) -> None:
        graph = InMemoryDependencyGraph()
        s1 = make_symbol("kt://Root", "Root")
        s2 = make_symbol("kt://Mid", "Mid")
        s3 = make_symbol("kt://Top", "Top")

        for s in (s1, s2, s3):
            graph.add_symbol(s)

        ev1 = EvidenceReference(
            evidence_type=EvidenceType.CALL_SITE,
            location=s2.location,
            description="Call from Mid to Root",
        )
        edge1 = DependencyEdge(
            source_symbol_id=s2.id,
            target_symbol_id=s1.id,
            edge_kind=EdgeKind.CALLS,
            confidence=ConfidenceLevel.VERIFIED,
            evidence=[ev1],
        )

        ev2 = EvidenceReference(
            evidence_type=EvidenceType.CALL_SITE,
            location=s3.location,
            description="Call from Top to Mid",
        )
        edge2 = DependencyEdge(
            source_symbol_id=s3.id,
            target_symbol_id=s2.id,
            edge_kind=EdgeKind.CALLS,
            confidence=ConfidenceLevel.POSSIBLE,
            evidence=[ev2],
        )

        graph.add_edge(edge1)
        graph.add_edge(edge2)

        path = [s1.id, s2.id, s3.id]
        conf = graph.calculate_path_confidence(path)
        assert conf == ConfidenceLevel.POSSIBLE  # Degraded to lowest confidence

        evidence = graph.collect_path_evidence(path)
        assert len(evidence) == 2
        assert any(e.description == "Call from Mid to Root" for e in evidence)
        assert any(e.description == "Call from Top to Mid" for e in evidence)

    def test_module_and_file_queries(self) -> None:
        graph = InMemoryDependencyGraph()
        s1 = make_symbol("kt://A", "A", file_path="core/src/main/kotlin/A.kt")
        s2 = make_symbol("kt://B", "B", file_path="core/src/main/kotlin/B.kt")
        s3 = make_symbol("kt://C", "C", file_path="feature/src/main/kotlin/C.kt")

        for s in (s1, s2, s3):
            graph.add_symbol(s)

        graph.add_module(":core", ["core/src/main/kotlin/A.kt", "core/src/main/kotlin/B.kt"])
        graph.add_module(":feature", ["feature/src/main/kotlin/C.kt"])

        assert graph.get_module_for_file("core/src/main/kotlin/A.kt") == ":core"
        assert graph.get_module_for_symbol(s3.id) == ":feature"

        core_syms = graph.get_symbols_in_module(":core")
        assert len(core_syms) == 2
        assert {s.name for s in core_syms} == {"A", "B"}

    def test_related_tests_and_missing_test_coverage(self) -> None:
        graph = InMemoryDependencyGraph()
        target = make_symbol(
            "kt://UserAuth", "UserAuth", file_path="app/src/main/kotlin/UserAuth.kt"
        )
        covered_sym = make_symbol(
            "kt://Profile", "Profile", file_path="app/src/main/kotlin/Profile.kt"
        )
        untested_sym = make_symbol(
            "kt://Billing", "Billing", file_path="app/src/main/kotlin/Billing.kt"
        )

        # Test symbol explicitly calling UserAuth
        test1 = make_symbol(
            "kt://UserAuthTest#testLogin",
            "testLogin",
            file_path="app/src/test/kotlin/UserAuthTest.kt",
            is_test=True,
        )
        # Test symbol matching Profile by file stem naming convention
        test2 = make_symbol(
            "kt://ProfileTest#testView",
            "testView",
            file_path="app/src/test/kotlin/ProfileTest.kt",
            is_test=True,
        )

        for s in (target, covered_sym, untested_sym, test1, test2):
            graph.add_symbol(s)

        graph.add_edge(
            DependencyEdge(
                source_symbol_id=test1.id,
                target_symbol_id=target.id,
                edge_kind=EdgeKind.CALLS,
            )
        )

        related = graph.get_related_tests({target.id})
        assert len(related) == 1
        assert related[0].id == test1.id

        related_profile = graph.get_related_tests({covered_sym.id})
        assert len(related_profile) == 1
        assert related_profile[0].id == test2.id

        missing = graph.get_missing_test_coverage({target.id, covered_sym.id, untested_sym.id})
        assert len(missing) == 1
        assert missing[0] == untested_sym.id
