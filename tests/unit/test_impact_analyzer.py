"""Unit tests for ImpactAnalyzer coordinator."""

from __future__ import annotations

from changeblast.adapters.graph import InMemoryDependencyGraph
from changeblast.analysis.impact import ImpactAnalyzer
from changeblast.models.changeset import ChangedFile, ChangeSet
from changeblast.models.common import (
    ChangeType,
    EdgeKind,
    Language,
    LineRange,
    Platform,
    RiskLevel,
    SourceLocation,
    SymbolKind,
    Visibility,
)
from changeblast.models.edge import DependencyEdge
from changeblast.models.repository import GradleModule, RepositoryProfile
from changeblast.models.symbol import SourceSymbol


def make_sym(
    sym_id: str,
    name: str,
    file_path: str,
    start_line: int,
    end_line: int,
    is_test: bool = False,
    is_entry_point: bool = False,
) -> SourceSymbol:
    return SourceSymbol(
        id=sym_id,
        name=name,
        qualified_name=f"com.example.app.feature.auth.{name}",
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


class TestImpactAnalyzer:
    """Validate end-to-end blast radius analysis, module attribution, and reporting."""

    def test_impact_analysis_direct_and_transitive_propagation(self) -> None:
        profile = RepositoryProfile(
            root_path="/mock/repo",
            platforms=[Platform.ANDROID],
            languages=[Language.KOTLIN],
            is_monorepo=False,
            source_roots=["feature/auth/src/main/kotlin"],
            test_roots=["feature/auth/src/test/kotlin"],
            build_files=["build.gradle.kts"],
            gradle_modules=[
                GradleModule(
                    name=":feature:auth",
                    path="feature/auth",
                    build_file="feature/auth/build.gradle.kts",
                    source_roots=["feature/auth/src/main/kotlin"],
                    test_roots=["feature/auth/src/test/kotlin"],
                )
            ],
            xcode_projects=[],
            swift_packages=[],
            vcs=None,
        )

        # Graph: AuthToken (modified) <- LoginService (calls AuthToken) <- LoginScreen (calls LoginService)
        graph = InMemoryDependencyGraph()
        s_token = make_sym(
            "kt://AuthToken", "AuthToken", "feature/auth/src/main/kotlin/AuthToken.kt", 10, 20
        )
        s_service = make_sym(
            "kt://LoginService",
            "LoginService",
            "feature/auth/src/main/kotlin/LoginService.kt",
            15,
            30,
        )
        s_screen = make_sym(
            "kt://LoginScreen",
            "LoginScreen",
            "feature/auth/src/main/kotlin/LoginScreen.kt",
            5,
            50,
            is_entry_point=True,
        )
        s_test = make_sym(
            "kt://AuthTokenTest",
            "AuthTokenTest",
            "feature/auth/src/test/kotlin/AuthTokenTest.kt",
            1,
            20,
            is_test=True,
        )

        for s in (s_token, s_service, s_screen, s_test):
            graph.add_symbol(s)

        # Edges
        graph.add_edge(
            DependencyEdge(
                source_symbol_id=s_service.id, target_symbol_id=s_token.id, edge_kind=EdgeKind.CALLS
            )
        )
        graph.add_edge(
            DependencyEdge(
                source_symbol_id=s_screen.id,
                target_symbol_id=s_service.id,
                edge_kind=EdgeKind.CALLS,
            )
        )
        graph.add_edge(
            DependencyEdge(
                source_symbol_id=s_test.id, target_symbol_id=s_token.id, edge_kind=EdgeKind.CALLS
            )
        )

        # Changeset modifying lines 10..12 of AuthToken.kt (signature change)
        changeset = ChangeSet(
            base_ref="HEAD~1",
            target_ref="HEAD",
            changed_files=[
                ChangedFile(
                    path="feature/auth/src/main/kotlin/AuthToken.kt",
                    change_type=ChangeType.MODIFIED,
                    changed_line_ranges=[LineRange(start_line=10, end_line=12)],
                )
            ],
            total_additions=2,
            total_deletions=1,
        )

        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(profile=profile, changeset=changeset, graph=graph, max_depth=5)

        # Assertions
        assert report.summary.directly_modified_symbols == 1
        assert report.summary.direct_impacts_count == 1  # LoginService
        assert report.summary.transitive_impacts_count == 1  # LoginScreen
        assert report.summary.affected_ui_components_count == 1  # LoginScreen is UI
        assert len(report.findings) == 3

        # Finding 0: AuthToken
        f0 = next(f for f in report.findings if f.depth == 0)
        assert f0.target_symbol.id == s_token.id
        assert f0.is_breaking is True
        assert ":feature:auth" in f0.affected_modules
        assert "auth" in f0.related_features

        # Finding 1: LoginService (depth 1)
        f1 = next(f for f in report.findings if f.depth == 1)
        assert f1.target_symbol.id == s_service.id
        assert f1.propagation_path == [s_token.id, s_service.id]

        # Finding 2: LoginScreen (depth 2)
        f2 = next(f for f in report.findings if f.depth == 2)
        assert f2.target_symbol.id == s_screen.id
        assert f2.is_ui_affected is True

        # Recommendations
        assert len(report.suggested_tests) >= 1
        assert any("AuthTokenTest.kt" in t for t in report.suggested_tests)

    def test_deleted_file_generates_breaking_change_and_critical_severity(self) -> None:
        profile = RepositoryProfile(
            root_path="/mock/repo",
            platforms=[Platform.ANDROID],
            languages=[Language.KOTLIN],
            is_monorepo=False,
            source_roots=[],
            test_roots=[],
            build_files=[],
            gradle_modules=[],
            xcode_projects=[],
            swift_packages=[],
            vcs=None,
        )
        graph = InMemoryDependencyGraph()
        sym = make_sym("kt://DeprecatedApi", "DeprecatedApi", "core/DeprecatedApi.kt", 1, 20)
        graph.add_symbol(sym)

        changeset = ChangeSet(
            base_ref="HEAD~1",
            target_ref="HEAD",
            changed_files=[
                ChangedFile(
                    path="core/DeprecatedApi.kt",
                    change_type=ChangeType.DELETED,
                    changed_line_ranges=[],
                )
            ],
            total_additions=0,
            total_deletions=20,
        )

        analyzer = ImpactAnalyzer()
        report = analyzer.analyze(profile=profile, changeset=changeset, graph=graph)

        assert report.summary.directly_modified_symbols == 1
        assert report.findings[0].is_breaking is True
        assert report.overall_risk.level == RiskLevel.CRITICAL
