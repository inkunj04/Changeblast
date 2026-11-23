"""Unit tests for ReportFormatter adapter."""

from __future__ import annotations

import json

from changeblast.adapters.reporters import ReportFormatter
from changeblast.models.changeset import ChangedFile, ChangeSet
from changeblast.models.common import (
    CURRENT_SCHEMA_VERSION,
    ChangeType,
    ConfidenceLevel,
    EvidenceType,
    Language,
    LineRange,
    Platform,
    RiskLevel,
    SourceLocation,
    SymbolKind,
    Visibility,
    WarningCategory,
)
from changeblast.models.evidence import EvidenceReference
from changeblast.models.finding import AnalysisWarning, ImpactFinding
from changeblast.models.report import ImpactReport, RiskAssessment, SummaryMetrics
from changeblast.models.repository import RepositoryProfile
from changeblast.models.symbol import SourceSymbol


def make_dummy_report() -> ImpactReport:
    loc = SourceLocation(
        file_path="app/Main.kt", start_line=1, start_column=0, end_line=10, end_column=1
    )
    sym = SourceSymbol(
        id="kt://MainActivity",
        name="MainActivity",
        qualified_name="com.example.MainActivity",
        kind=SymbolKind.CLASS,
        language=Language.KOTLIN,
        visibility=Visibility.PUBLIC,
        location=loc,
        is_entry_point=True,
    )
    finding = ImpactFinding(
        finding_id="f_main",
        target_symbol=sym,
        root_changed_symbol_id=sym.id,
        depth=0,
        propagation_path=[sym.id],
        evidence=[
            EvidenceReference(
                evidence_type=EvidenceType.DIRECT_DIFF_MATCH,
                location=loc,
                description="Direct match in Main.kt",
            )
        ],
        is_breaking=True,
        is_ui_affected=True,
        suggested_tests=[],
        severity=RiskLevel.HIGH,
        confidence=ConfidenceLevel.VERIFIED,
        affected_modules=[":app"],
        related_features=["auth"],
    )
    warning = AnalysisWarning(
        warning_id="w_test",
        category=WarningCategory.MISSING_TEST_COVERAGE,
        message="1 component lacks automated tests",
        remediation="Add unit test",
    )
    return ImpactReport(
        report_id="rpt_test123",
        repository=RepositoryProfile(
            root_path="/test",
            platforms=[Platform.ANDROID],
            languages=[Language.KOTLIN],
            is_monorepo=False,
            source_roots=["app/src/main"],
            test_roots=["app/src/test"],
            build_files=["build.gradle.kts"],
            gradle_modules=[],
            xcode_projects=[],
            swift_packages=[],
            vcs=None,
        ),
        changeset=ChangeSet(
            base_ref="HEAD~1",
            target_ref="HEAD",
            changed_files=[
                ChangedFile(
                    path="app/Main.kt",
                    change_type=ChangeType.MODIFIED,
                    changed_line_ranges=[LineRange(start_line=1, end_line=5)],
                )
            ],
            total_additions=5,
            total_deletions=2,
        ),
        summary=SummaryMetrics(
            total_files_changed=1,
            directly_modified_symbols=1,
            direct_impacts_count=0,
            transitive_impacts_count=0,
            affected_ui_components_count=1,
            suggested_tests_count=1,
            affected_modules_count=1,
            missing_test_coverage_count=1,
        ),
        overall_risk=RiskAssessment(
            level=RiskLevel.HIGH,
            confidence=ConfidenceLevel.VERIFIED,
            score=55.0,
            reasons=["Directly modified 1 source symbol", "UI component affected"],
            breaking_change_signals=["Potential breaking change in MainActivity"],
        ),
        findings=[finding],
        warnings=[warning],
        suggested_tests=["app/src/test/MainActivityTest.kt"],
        affected_modules=[":app"],
        missing_test_coverage=["kt://MainActivity"],
    )


class TestReportFormatter:
    """Validate JSON, Markdown, and terminal summary outputs."""

    def test_format_json_valid_schema(self) -> None:
        formatter = ReportFormatter()
        report = make_dummy_report()
        json_str = formatter.format_json(report)
        data = json.loads(json_str)

        assert data["schema_version"] == CURRENT_SCHEMA_VERSION
        assert data["report_id"] == "rpt_test123"
        assert data["overall_risk"]["level"] == "high"
        assert len(data["findings"]) == 1
        assert data["summary"]["affected_ui_components_count"] == 1

    def test_format_markdown_contains_all_sections(self) -> None:
        formatter = ReportFormatter()
        report = make_dummy_report()
        md = formatter.format_markdown(report)

        assert "# ⚠️ ChangeBlast Impact Report" in md
        assert "**Overall Risk**: `HIGH`" in md
        assert "## Summary Metrics" in md
        assert "| **Files Changed** | 1 |" in md
        assert "### ⚠️ Potential Breaking Changes" in md
        assert "## Directly Modified Symbols" in md
        assert "| `MainActivity` | `class` |" in md
        assert "## Affected Modules" in md
        assert "- `:app`" in md
        assert "## Recommended Regression Tests" in md
        assert "`app/src/test/MainActivityTest.kt`" in md
        assert "## 🔍 Analysis Warnings & Limitations" in md

    def test_format_summary_concise(self) -> None:
        formatter = ReportFormatter()
        report = make_dummy_report()
        summary = formatter.format_summary(report)

        assert "ChangeBlast Analysis: /test" in summary
        assert "Risk Level: HIGH" in summary
        assert "Files Changed: 1" in summary
        assert "Recommended Tests:" in summary
