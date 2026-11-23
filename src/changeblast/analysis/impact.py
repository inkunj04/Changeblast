"""Impact analysis coordinator extracting blast radius and assembling reports."""

from __future__ import annotations

import hashlib

from changeblast.adapters.graph.memory import InMemoryDependencyGraph
from changeblast.analysis.correlator import SymbolDiffCorrelator
from changeblast.analysis.risk import RiskEngine
from changeblast.models.changeset import ChangeSet
from changeblast.models.common import (
    ConfidenceLevel,
    EvidenceType,
    RiskLevel,
    WarningCategory,
)
from changeblast.models.evidence import EvidenceReference
from changeblast.models.finding import AnalysisWarning, ImpactFinding
from changeblast.models.report import ImpactReport, SummaryMetrics
from changeblast.models.repository import RepositoryProfile
from changeblast.models.symbol import SourceSymbol


class ImpactAnalyzer:
    """Coordinates changeset symbol correlation, graph traversal, and report generation."""

    def __init__(
        self,
        correlator: SymbolDiffCorrelator | None = None,
        risk_engine: RiskEngine | None = None,
    ) -> None:
        self.correlator = correlator or SymbolDiffCorrelator()
        self.risk_engine = risk_engine or RiskEngine()

    def analyze(
        self,
        profile: RepositoryProfile,
        changeset: ChangeSet,
        graph: InMemoryDependencyGraph,
        max_depth: int = 10,
    ) -> ImpactReport:
        """Execute impact analysis across repository profile and changeset."""
        directly_modified = self.correlator.correlate(changeset, graph)

        findings_by_target: dict[str, ImpactFinding] = {}
        warnings: list[AnalysisWarning] = []

        # 1. Process directly modified and deleted symbols (Depth 0)
        for dm in directly_modified:
            sym = dm.symbol
            is_ui = self._is_ui_component(sym)
            mod_name = self._resolve_module(sym.location.file_path, profile)
            features = self._extract_features(sym.location.file_path, sym.qualified_name)

            evidence = [
                EvidenceReference(
                    evidence_type=EvidenceType.DIRECT_DIFF_MATCH,
                    location=sym.location,
                    description=f"Direct diff modification in '{sym.location.file_path}' "
                    f"({'deleted' if dm.is_deleted else 'signature changed' if dm.is_signature_modified else 'body changed'})",
                )
            ]

            finding_id = hashlib.sha256(f"finding:0:{sym.id}".encode()).hexdigest()[:16]

            # Direct finding severity
            if dm.is_deleted or (dm.is_signature_modified and sym.is_entry_point):
                severity = RiskLevel.CRITICAL
            elif dm.is_signature_modified or is_ui:
                severity = RiskLevel.HIGH
            else:
                severity = RiskLevel.MEDIUM

            findings_by_target[sym.id] = ImpactFinding(
                finding_id=finding_id,
                target_symbol=sym,
                root_changed_symbol_id=sym.id,
                depth=0,
                propagation_path=[sym.id],
                evidence=evidence,
                is_breaking=dm.is_signature_modified or dm.is_deleted,
                is_ui_affected=is_ui,
                suggested_tests=[],
                severity=severity,
                confidence=ConfidenceLevel.VERIFIED,
                affected_modules=[mod_name] if mod_name else [],
                related_features=features,
            )

            # 2. Traverse upstream reverse callers/dependents (Depth >= 1)
            dependents = graph.get_transitive_dependents(sym.id, max_depth=max_depth)
            for dep_sym, depth, path in dependents:
                # Test entities are recorded as test targets, not production blast radius components
                if dep_sym.is_test:
                    continue

                target_id = dep_sym.id
                # If target already recorded with shallower depth, keep shortest path
                if target_id in findings_by_target and findings_by_target[target_id].depth <= depth:
                    continue

                dep_is_ui = self._is_ui_component(dep_sym)
                dep_mod = self._resolve_module(dep_sym.location.file_path, profile)
                dep_features = self._extract_features(
                    dep_sym.location.file_path, dep_sym.qualified_name
                )
                confidence = graph.calculate_path_confidence(path)
                path_evidence = graph.collect_path_evidence(path)

                # Severity for transitive dependents
                if dep_is_ui or depth == 1:
                    dep_severity = RiskLevel.HIGH if dep_is_ui else RiskLevel.MEDIUM
                elif depth <= 3:
                    dep_severity = RiskLevel.MEDIUM
                else:
                    dep_severity = RiskLevel.LOW

                finding_id = hashlib.sha256(f"finding:{depth}:{target_id}".encode()).hexdigest()[
                    :16
                ]

                findings_by_target[target_id] = ImpactFinding(
                    finding_id=finding_id,
                    target_symbol=dep_sym,
                    root_changed_symbol_id=sym.id,
                    depth=depth,
                    propagation_path=path,
                    evidence=path_evidence,
                    is_breaking=False,
                    is_ui_affected=dep_is_ui,
                    suggested_tests=[],
                    severity=dep_severity,
                    confidence=confidence,
                    affected_modules=[dep_mod] if dep_mod else [],
                    related_features=dep_features,
                )

        all_findings = sorted(
            findings_by_target.values(),
            key=lambda f: (f.depth, f.target_symbol.id),
        )
        impacted_symbol_ids = {f.target_symbol.id for f in all_findings}

        # 3. Identify all affected modules
        affected_modules_set: set[str] = set()
        for f in all_findings:
            affected_modules_set.update(f.affected_modules)
        affected_modules = sorted(list(affected_modules_set))

        # 4. Related tests and recommendations
        related_test_symbols = graph.get_related_tests(impacted_symbol_ids)
        suggested_tests = sorted(list({ts.location.file_path for ts in related_test_symbols}))

        # 5. Missing test coverage detection
        missing_coverage = graph.get_missing_test_coverage(impacted_symbol_ids)
        if missing_coverage:
            warnings.append(
                AnalysisWarning(
                    warning_id=hashlib.sha256(b"missing_test_coverage").hexdigest()[:16],
                    category=WarningCategory.MISSING_TEST_COVERAGE,
                    message=f"{len(missing_coverage)} impacted components have no identified automated test coverage.",
                    remediation="Add unit or integration tests covering modified symbols.",
                )
            )

        # 6. Cycle detection in affected subgraph
        cycles = graph.detect_cycles()
        affected_cycles = [c for c in cycles if any(sid in impacted_symbol_ids for sid in c)]
        for c in affected_cycles:
            cycle_str = " -> ".join(c)
            warnings.append(
                AnalysisWarning(
                    warning_id=hashlib.sha256(f"cycle:{cycle_str}".encode()).hexdigest()[:16],
                    category=WarningCategory.CIRCULAR_DEPENDENCY,
                    message=f"Circular dependency cycle detected: {cycle_str}",
                    remediation="Break circular reference by extracting shared interface or protocol.",
                )
            )

        # 7. Evaluate overall risk
        overall_risk = self.risk_engine.evaluate(
            findings=all_findings,
            affected_modules=affected_modules,
            missing_test_count=len(missing_coverage),
            is_monorepo=profile.is_monorepo,
        )

        # 8. Assemble summary metrics
        direct_count = sum(1 for f in all_findings if f.depth == 0)
        direct_dependents_count = sum(1 for f in all_findings if f.depth == 1)
        transitive_dependents_count = sum(1 for f in all_findings if f.depth >= 2)
        ui_count = sum(1 for f in all_findings if f.is_ui_affected)

        summary = SummaryMetrics(
            total_files_changed=len(changeset.changed_files),
            directly_modified_symbols=direct_count,
            direct_impacts_count=direct_dependents_count,
            transitive_impacts_count=transitive_dependents_count,
            affected_ui_components_count=ui_count,
            suggested_tests_count=len(suggested_tests),
            affected_modules_count=len(affected_modules),
            missing_test_coverage_count=len(missing_coverage),
        )

        report_seed = f"{profile.root_path}:{changeset.total_additions}:{changeset.total_deletions}:{len(all_findings)}"
        report_id = f"rpt_{hashlib.sha256(report_seed.encode()).hexdigest()[:16]}"

        return ImpactReport(
            report_id=report_id,
            repository=profile,
            changeset=changeset,
            summary=summary,
            overall_risk=overall_risk,
            findings=all_findings,
            warnings=warnings,
            suggested_tests=suggested_tests,
            affected_modules=affected_modules,
            missing_test_coverage=missing_coverage,
        )

    # ----------------- Helper Heuristics -----------------

    def _is_ui_component(self, sym: SourceSymbol) -> bool:
        """Determine whether symbol represents a user-facing UI component."""
        if sym.is_entry_point:
            return True
        name_lower = sym.name.lower()
        ui_indicators = (
            "activity",
            "fragment",
            "view",
            "screen",
            "controller",
            "dialog",
            "sheet",
            "widget",
            "page",
            "composable",
        )
        return any(ind in name_lower for ind in ui_indicators)

    def _resolve_module(self, file_path: str, profile: RepositoryProfile) -> str:
        """Attribute a file path to its containing module or package."""
        norm_file = file_path.replace("\\", "/")
        # 1. Check Gradle modules
        for gm in profile.gradle_modules:
            gm_path = gm.path.replace("\\", "/")
            if norm_file.startswith(gm_path) or f"/{gm_path}/" in f"/{norm_file}/":
                return gm.name

        # 2. Check Xcode projects & targets
        for xp in profile.xcode_projects:
            xp_path = xp.path.replace("\\", "/")
            if norm_file.startswith(xp_path):
                return xp.name

        # 3. Check Swift packages
        for sp in profile.swift_packages:
            sp_path = sp.path.replace("\\", "/")
            if norm_file.startswith(sp_path):
                return sp.name

        # 4. Fallback based on top-level folder
        parts = norm_file.split("/")
        if len(parts) > 1 and parts[0] in {"android", "ios", "app", "core", "features"}:
            return f":{parts[0]}"
        return ":root"

    def _extract_features(self, file_path: str, qualified_name: str) -> list[str]:
        """Extract architectural feature domain tags from path and package naming."""
        features: set[str] = set()
        norm_path = file_path.replace("\\", "/").lower()
        parts = norm_path.split("/")

        # Check path segments after 'feature' or 'features'
        for i, part in enumerate(parts):
            if part in {"feature", "features"} and i + 1 < len(parts):
                features.add(parts[i + 1])
            elif part in {"auth", "login", "checkout", "payment", "settings", "profile", "feed"}:
                features.add(part)

        # Check package qualifier segments
        q_lower = qualified_name.lower()
        for domain in ("auth", "checkout", "payment", "feed", "settings", "search", "onboarding"):
            if f".{domain}." in q_lower or q_lower.endswith(f".{domain}"):
                features.add(domain)

        return sorted(list(features))
