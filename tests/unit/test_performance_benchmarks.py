"""Performance QA benchmarks measuring analysis latency, memory usage, and graph scalability."""

from __future__ import annotations

import time
import tracemalloc

from changeblast.adapters.graph import InMemoryDependencyGraph
from changeblast.adapters.reporters import ReportFormatter
from changeblast.analysis import ImpactAnalyzer
from changeblast.models import (
    ChangedFile,
    ChangeSet,
    ChangeType,
    ConfidenceLevel,
    DependencyEdge,
    EdgeKind,
    Language,
    LineRange,
    Platform,
    RepositoryProfile,
    SourceLocation,
    SourceSymbol,
    SymbolKind,
    Visibility,
)


def generate_synthetic_graph(
    num_files: int,
    symbols_per_file: int = 5,
    edges_per_symbol: int = 4,
) -> tuple[InMemoryDependencyGraph, list[SourceSymbol], RepositoryProfile, ChangeSet]:
    """Deterministically construct a synthetic mobile codebase graph for benchmarking."""
    graph = InMemoryDependencyGraph()
    symbols: list[SourceSymbol] = []
    source_roots: list[str] = ["app/src/main/kotlin", "ios/App"]

    profile = RepositoryProfile(
        root_path="/benchmark/repo",
        platforms=[Platform.ANDROID, Platform.IOS],
        languages=[Language.KOTLIN, Language.SWIFT],
        is_monorepo=True,
        source_roots=source_roots,
        test_roots=["app/src/test/kotlin", "ios/Tests"],
        build_files=["build.gradle.kts", "Package.swift"],
        gradle_modules=[],
        xcode_projects=[],
        swift_packages=[],
    )

    for f_idx in range(num_files):
        is_ios = f_idx % 2 == 1
        ext = "swift" if is_ios else "kt"
        root = source_roots[1] if is_ios else source_roots[0]
        file_path = f"{root}/Component_{f_idx}.{ext}"
        graph.add_file(file_path)

        for s_idx in range(symbols_per_file):
            sym_id = f"{'swift' if is_ios else 'kt'}://com.benchmark.Comp{f_idx}#sym{s_idx}"
            sym = SourceSymbol(
                id=sym_id,
                name=f"Comp{f_idx}Sym{s_idx}",
                qualified_name=f"com.benchmark.Comp{f_idx}.sym{s_idx}",
                kind=SymbolKind.CLASS if s_idx == 0 else SymbolKind.METHOD,
                language=Language.SWIFT if is_ios else Language.KOTLIN,
                visibility=Visibility.PUBLIC,
                location=SourceLocation(
                    file_path=file_path,
                    start_line=s_idx * 20 + 1,
                    end_line=s_idx * 20 + 18,
                    start_column=0,
                    end_column=10,
                ),
                is_entry_point=(s_idx == 0 and f_idx % 5 == 0),
            )
            symbols.append(sym)
            graph.add_symbol(sym)

    # Interconnect symbols with dependency edges
    num_symbols = len(symbols)
    for i, sym in enumerate(symbols):
        for e in range(1, edges_per_symbol + 1):
            target_idx = (i + e * 7) % num_symbols
            if target_idx != i:
                target_sym = symbols[target_idx]
                edge = DependencyEdge(
                    source_symbol_id=sym.id,
                    target_symbol_id=target_sym.id,
                    edge_kind=EdgeKind.CALLS,
                    confidence=ConfidenceLevel.VERIFIED,
                )
                graph.add_edge(edge)

    # Target changeset modifying 2 central files
    changed_file = ChangedFile(
        path=f"{source_roots[0]}/Component_0.kt",
        change_type=ChangeType.MODIFIED,
        changed_line_ranges=[LineRange(start_line=1, end_line=10)],
    )
    changeset = ChangeSet(
        base_ref="main",
        target_ref="feature",
        changed_files=[changed_file],
        total_additions=10,
        total_deletions=2,
    )

    return graph, symbols, profile, changeset


class TestPerformanceBenchmarks:
    """Benchmark analysis runtime latency and memory across small, medium, and large topologies."""

    def test_small_repository_benchmark(self) -> None:
        """Benchmark Small Repository: ~10 files, ~50 symbols, ~200 edges."""
        graph, symbols, profile, changeset = generate_synthetic_graph(
            num_files=10, symbols_per_file=5, edges_per_symbol=4
        )
        assert graph.node_count == 50
        assert graph.edge_count >= 150

        tracemalloc.start()
        t_start = time.perf_counter()

        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(profile=profile, changeset=changeset, graph=graph, max_depth=10)
        formatter = ReportFormatter()
        json_out = formatter.format_json(report)
        md_out = formatter.format_markdown(report)

        elapsed = time.perf_counter() - t_start
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak_mem / (1024 * 1024)

        # Performance SLOs: < 0.2s, < 20 MB peak
        assert elapsed < 0.5, f"Small benchmark exceeded latency SLO: {elapsed:.3f}s"
        assert peak_mb < 25.0, f"Small benchmark exceeded memory SLO: {peak_mb:.2f} MB"
        assert len(json_out) > 0
        assert len(md_out) > 0

    def test_medium_repository_benchmark(self) -> None:
        """Benchmark Medium Repository: ~100 files, ~500 symbols, ~2,000 edges."""
        graph, symbols, profile, changeset = generate_synthetic_graph(
            num_files=100, symbols_per_file=5, edges_per_symbol=4
        )
        assert graph.node_count == 500
        assert graph.edge_count >= 1500

        tracemalloc.start()
        t_start = time.perf_counter()

        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(profile=profile, changeset=changeset, graph=graph, max_depth=10)
        formatter = ReportFormatter()
        json_out = formatter.format_json(report)

        elapsed = time.perf_counter() - t_start
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak_mem / (1024 * 1024)

        # Performance SLOs: < 1.0s, < 50 MB peak
        assert elapsed < 1.5, f"Medium benchmark exceeded latency SLO: {elapsed:.3f}s"
        assert peak_mb < 60.0, f"Medium benchmark exceeded memory SLO: {peak_mb:.2f} MB"
        assert len(json_out) > 0

    def test_large_repository_benchmark(self) -> None:
        """Benchmark Large Repository: ~500 files, ~2,500 symbols, ~10,000 edges."""
        graph, symbols, profile, changeset = generate_synthetic_graph(
            num_files=500, symbols_per_file=5, edges_per_symbol=4
        )
        assert graph.node_count == 2500
        assert graph.edge_count >= 7500

        tracemalloc.start()
        t_start = time.perf_counter()

        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(profile=profile, changeset=changeset, graph=graph, max_depth=10)
        formatter = ReportFormatter()
        json_out = formatter.format_json(report)
        summary = formatter.format_summary(report)

        elapsed = time.perf_counter() - t_start
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak_mem / (1024 * 1024)

        # Performance SLOs: < 3.0s, < 120 MB peak
        assert elapsed < 4.0, f"Large benchmark exceeded latency SLO: {elapsed:.3f}s"
        assert peak_mb < 120.0, f"Large benchmark exceeded memory SLO: {peak_mb:.2f} MB"
        assert len(json_out) > 0
        assert len(summary) > 0
