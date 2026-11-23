"""In-memory directed multi-graph for mobile dependency and call relationship traversal."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Sequence

from changeblast.models.common import ConfidenceLevel, EdgeKind, EvidenceType
from changeblast.models.edge import DependencyEdge
from changeblast.models.evidence import EvidenceReference
from changeblast.models.symbol import SourceSymbol
from changeblast.ports.graph import IDependencyGraphAdapter


class InMemoryDependencyGraph(IDependencyGraphAdapter):
    """In-memory directed multigraph managing symbols, files, modules, and tests.

    Supports forward dependencies, upstream reverse caller traversal (blast radius),
    bounded depth recursion, cycle detection, and confidence calculation.
    """

    def __init__(self) -> None:
        self._symbols: dict[str, SourceSymbol] = {}
        self._file_to_symbols: dict[str, set[str]] = defaultdict(set)
        self._module_to_files: dict[str, set[str]] = defaultdict(set)
        self._file_to_module: dict[str, str] = {}
        # Outgoing edges: source -> [edges to targets] (Forward dependencies)
        self._outgoing: dict[str, list[DependencyEdge]] = defaultdict(list)
        # Incoming edges: target -> [edges from sources] (Reverse callers / dependents)
        self._incoming: dict[str, list[DependencyEdge]] = defaultdict(list)

    # ----------------- Port Implementations -----------------

    def add_symbol(self, symbol: SourceSymbol) -> None:
        """Register a symbol node in the graph."""
        self._symbols[symbol.id] = symbol
        norm_file = symbol.location.file_path.replace("\\", "/")
        self._file_to_symbols[norm_file].add(symbol.id)

    def add_edge(self, edge: DependencyEdge) -> None:
        """Register a directed dependency or invocation edge between two symbols."""
        self._outgoing[edge.source_symbol_id].append(edge)
        self._incoming[edge.target_symbol_id].append(edge)

    def get_symbol(self, symbol_id: str) -> SourceSymbol | None:
        """Retrieve symbol node by its unique identifier."""
        return self._symbols.get(symbol_id)

    @property
    def node_count(self) -> int:
        """Total number of registered symbol nodes."""
        return len(self._symbols)

    @property
    def edge_count(self) -> int:
        """Total number of registered dependency edges."""
        return sum(len(edges) for edges in self._outgoing.values())

    def get_direct_dependents(self, symbol_id: str) -> list[SourceSymbol]:
        """Find immediate upstream callers or subclasses that depend on the given symbol."""
        dependents: list[SourceSymbol] = []
        seen_ids: set[str] = set()

        for edge in self._incoming.get(symbol_id, []):
            caller_id = edge.source_symbol_id
            if caller_id not in seen_ids:
                seen_ids.add(caller_id)
                sym = self._symbols.get(caller_id)
                if sym:
                    dependents.append(sym)
        return sorted(dependents, key=lambda s: s.id)

    def get_transitive_dependents(
        self,
        symbol_id: str,
        max_depth: int = 10,
    ) -> list[tuple[SourceSymbol, int, list[str]]]:
        """Traverse upstream reverse dependents (callers/subclasses) up to max_depth.

        Returns:
            List of (impacted_symbol, depth, propagation_path_symbol_ids).
        """
        results: list[tuple[SourceSymbol, int, list[str]]] = []
        visited: dict[str, int] = {symbol_id: 0}
        # Queue entries: (current_symbol_id, current_depth, propagation_path)
        queue: deque[tuple[str, int, list[str]]] = deque([(symbol_id, 0, [symbol_id])])

        while queue:
            curr_id, depth, path = queue.popleft()
            if depth >= max_depth:
                continue

            for edge in self._incoming.get(curr_id, []):
                caller_id = edge.source_symbol_id
                # Avoid circular loops along current traversal path
                if caller_id in path:
                    continue

                nxt_depth = depth + 1
                if caller_id not in visited or nxt_depth < visited[caller_id]:
                    visited[caller_id] = nxt_depth
                    nxt_path = path + [caller_id]
                    sym = self._symbols.get(caller_id)
                    if sym:
                        results.append((sym, nxt_depth, nxt_path))
                    queue.append((caller_id, nxt_depth, nxt_path))

        # Sort primarily by depth, secondarily by symbol ID for deterministic stability
        results.sort(key=lambda item: (item[1], item[0].id))
        return results

    def get_direct_dependencies(self, symbol_id: str) -> list[SourceSymbol]:
        """Find immediate downstream callees or dependencies required by given symbol."""
        dependencies: list[SourceSymbol] = []
        seen_ids: set[str] = set()

        for edge in self._outgoing.get(symbol_id, []):
            target_id = edge.target_symbol_id
            if target_id not in seen_ids:
                seen_ids.add(target_id)
                sym = self._symbols.get(target_id)
                if sym:
                    dependencies.append(sym)
        return sorted(dependencies, key=lambda s: s.id)

    def get_transitive_dependencies(
        self,
        symbol_id: str,
        max_depth: int = 10,
    ) -> list[tuple[SourceSymbol, int, list[str]]]:
        """Traverse downstream dependencies up to max_depth."""
        results: list[tuple[SourceSymbol, int, list[str]]] = []
        visited: dict[str, int] = {symbol_id: 0}
        queue: deque[tuple[str, int, list[str]]] = deque([(symbol_id, 0, [symbol_id])])

        while queue:
            curr_id, depth, path = queue.popleft()
            if depth >= max_depth:
                continue

            for edge in self._outgoing.get(curr_id, []):
                target_id = edge.target_symbol_id
                if target_id in path:
                    continue

                nxt_depth = depth + 1
                if target_id not in visited or nxt_depth < visited[target_id]:
                    visited[target_id] = nxt_depth
                    nxt_path = path + [target_id]
                    sym = self._symbols.get(target_id)
                    if sym:
                        results.append((sym, nxt_depth, nxt_path))
                    queue.append((target_id, nxt_depth, nxt_path))

        results.sort(key=lambda item: (item[1], item[0].id))
        return results

    def detect_cycles(self) -> list[list[str]]:
        """Detect circular dependency loops in the graph.

        Returns:
            List of normalized cycle paths: e.g. [['A', 'B', 'C', 'A']].
        """
        visited: set[str] = set()
        rec_stack: dict[str, int] = {}
        path: list[str] = []
        cycles: list[list[str]] = []
        seen_cycle_fingerprints: set[tuple[str, ...]] = set()

        def dfs(node: str) -> None:
            rec_stack[node] = len(path)
            path.append(node)
            visited.add(node)

            for edge in self._outgoing.get(node, []):
                target = edge.target_symbol_id
                if target in rec_stack:
                    # Found a back-edge indicating a directed cycle
                    start_idx = rec_stack[target]
                    cycle_nodes = path[start_idx:] + [target]
                    # Normalize cycle: rotate so minimum element is at index 0
                    nodes_without_dup = cycle_nodes[:-1]
                    min_elem = min(nodes_without_dup)
                    min_idx = nodes_without_dup.index(min_elem)
                    normalized = tuple(
                        nodes_without_dup[min_idx:] + nodes_without_dup[:min_idx] + [min_elem]
                    )
                    if normalized not in seen_cycle_fingerprints:
                        seen_cycle_fingerprints.add(normalized)
                        cycles.append(list(normalized))
                elif target not in visited:
                    dfs(target)

            path.pop()
            del rec_stack[node]

        for node in sorted(self._symbols.keys()):
            if node not in visited:
                dfs(node)

        return sorted(cycles, key=lambda c: (len(c), c[0]))

    # ----------------- File, Module, and Node Queries -----------------

    def add_file(self, file_path: str, module_name: str | None = None) -> None:
        """Register a source file and optional module association."""
        norm_path = file_path.replace("\\", "/")
        if norm_path not in self._file_to_symbols:
            self._file_to_symbols[norm_path] = set()
        if module_name:
            self._file_to_module[norm_path] = module_name
            self._module_to_files[module_name].add(norm_path)

    def add_module(self, module_name: str, file_paths: Sequence[str]) -> None:
        """Register a module and its associated source file paths."""
        for fp in file_paths:
            self.add_file(fp, module_name=module_name)

    def get_symbols_in_file(self, file_path: str) -> list[SourceSymbol]:
        """Retrieve all symbols declared within a given file."""
        norm_path = file_path.replace("\\", "/")
        sym_ids = self._file_to_symbols.get(norm_path, set())
        symbols = [self._symbols[sid] for sid in sym_ids if sid in self._symbols]
        return sorted(symbols, key=lambda s: s.location.start_line)

    def get_symbols_in_module(self, module_name: str) -> list[SourceSymbol]:
        """Retrieve all symbols declared within a given module."""
        symbols: list[SourceSymbol] = []
        for file_path in self._module_to_files.get(module_name, set()):
            symbols.extend(self.get_symbols_in_file(file_path))
        return sorted(symbols, key=lambda s: s.id)

    def get_module_for_file(self, file_path: str) -> str | None:
        """Look up the module containing the given file."""
        norm_path = file_path.replace("\\", "/")
        return self._file_to_module.get(norm_path)

    def get_module_for_symbol(self, symbol_id: str) -> str | None:
        """Look up the module containing the given symbol."""
        sym = self._symbols.get(symbol_id)
        if not sym:
            return None
        return self.get_module_for_file(sym.location.file_path)

    def get_test_symbols(self) -> list[SourceSymbol]:
        """Retrieve all registered symbols designated as test entities."""
        return [sym for sym in self._symbols.values() if sym.is_test]

    def get_related_tests(self, symbol_ids: set[str]) -> list[SourceSymbol]:
        """Identify tests that cover any of the given symbols.

        Tests are identified if:
        1. The test symbol directly or transitively invokes the target symbol.
        2. The test file name matches standard test naming conventions for the symbol's file.
        """
        related_tests: dict[str, SourceSymbol] = {}

        # 1. Reachable tests through call graph
        for target_id in symbol_ids:
            for test_sym, _depth, _path in self.get_transitive_dependents(target_id):
                if test_sym.is_test:
                    related_tests[test_sym.id] = test_sym

        # 2. File-level test convention matching (e.g. FooTest.kt or FooSpec.swift)
        target_file_stems = {
            self._symbols[sid].location.file_path.split("/")[-1].split(".")[0].lower()
            for sid in symbol_ids
            if sid in self._symbols
        }

        for test_sym in self.get_test_symbols():
            test_file_name = test_sym.location.file_path.split("/")[-1].lower()
            for stem in target_file_stems:
                if stem and (
                    test_file_name.startswith(stem)
                    or f"{stem}test" in test_file_name
                    or f"{stem}spec" in test_file_name
                ):
                    related_tests[test_sym.id] = test_sym
                    break

        return sorted(related_tests.values(), key=lambda s: s.id)

    def get_missing_test_coverage(self, symbol_ids: set[str]) -> list[str]:
        """Identify non-test symbols that have zero test coverage."""
        missing: list[str] = []
        for sid in symbol_ids:
            sym = self._symbols.get(sid)
            if not sym or sym.is_test:
                continue
            related = self.get_related_tests({sid})
            if not related:
                missing.append(sid)
        return sorted(missing)

    # ----------------- Evidence & Confidence Utilities -----------------

    def get_edges_between(self, from_id: str, to_id: str) -> list[DependencyEdge]:
        """Retrieve all edges directed from from_id to to_id."""
        return [e for e in self._outgoing.get(from_id, []) if e.target_symbol_id == to_id]

    def calculate_path_confidence(self, path: Sequence[str]) -> ConfidenceLevel:
        """Calculate aggregate confidence along a symbol path.

        Confidence degrades along the chain to the lowest confidence link.
        """
        if len(path) <= 1:
            return ConfidenceLevel.VERIFIED

        lowest = ConfidenceLevel.VERIFIED
        # Order of confidence degradation:
        # VERIFIED > STRONG_INFERENCE > POSSIBLE > UNKNOWN
        order = {
            ConfidenceLevel.VERIFIED: 4,
            ConfidenceLevel.STRONG_INFERENCE: 3,
            ConfidenceLevel.POSSIBLE: 2,
            ConfidenceLevel.UNKNOWN: 1,
        }

        # For blast radius, propagation path is [root, step1, step2, ... target]
        # where step(i+1) calls step(i). Look for edges in either direction.
        for i in range(len(path) - 1):
            s1 = path[i]
            s2 = path[i + 1]
            edges = self.get_edges_between(s2, s1) or self.get_edges_between(s1, s2)
            if not edges:
                # Inferred link without explicit edge
                lowest = ConfidenceLevel.STRONG_INFERENCE
            else:
                for edge in edges:
                    if order.get(edge.confidence, 1) < order.get(lowest, 4):
                        lowest = edge.confidence

        return lowest

    def collect_path_evidence(self, path: Sequence[str]) -> list[EvidenceReference]:
        """Collate verifiable evidence references along a propagation path."""
        evidence_list: list[EvidenceReference] = []

        for i in range(len(path) - 1):
            s_from = path[i]
            s_to = path[i + 1]
            edges = self.get_edges_between(s_to, s_from) or self.get_edges_between(s_from, s_to)
            for e in edges:
                evidence_list.extend(e.evidence)
                if not e.evidence and e.location:
                    evidence_list.append(
                        EvidenceReference(
                            evidence_type=EvidenceType.CALL_SITE
                            if e.edge_kind == EdgeKind.CALLS
                            else EvidenceType.TYPE_REFERENCE,
                            location=e.location,
                            description=f"Dependency edge ({e.edge_kind}) linking {s_from} to {s_to}",
                        )
                    )

        # Fallback if no specific edge evidence was recorded
        if not evidence_list and path and path[0] in self._symbols:
            root_sym = self._symbols[path[0]]
            evidence_list.append(
                EvidenceReference(
                    evidence_type=EvidenceType.DIRECT_DIFF_MATCH,
                    location=root_sym.location,
                    description=f"Root modification detected at {root_sym.name}",
                )
            )

        return evidence_list
