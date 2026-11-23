"""Unit tests for transparent rule-based RiskEngine."""

from __future__ import annotations

from changeblast.analysis.risk import RiskEngine
from changeblast.models.common import (
    ConfidenceLevel,
    EvidenceType,
    Language,
    RiskLevel,
    SourceLocation,
    SymbolKind,
    Visibility,
)
from changeblast.models.evidence import EvidenceReference
from changeblast.models.finding import ImpactFinding
from changeblast.models.symbol import SourceSymbol


def make_finding(
    sym_id: str,
    name: str,
    depth: int = 0,
    is_breaking: bool = False,
    is_ui_affected: bool = False,
    confidence: ConfidenceLevel = ConfidenceLevel.VERIFIED,
    modules: list[str] | None = None,
) -> ImpactFinding:
    sym = SourceSymbol(
        id=sym_id,
        name=name,
        qualified_name=f"com.example.{name}",
        kind=SymbolKind.CLASS if "Activity" in name or "View" in name else SymbolKind.METHOD,
        language=Language.KOTLIN,
        visibility=Visibility.PUBLIC,
        location=SourceLocation(
            file_path="app/App.kt", start_line=1, start_column=0, end_line=10, end_column=1
        ),
        is_entry_point="Activity" in name or "View" in name,
    )
    return ImpactFinding(
        finding_id=f"f_{name}",
        target_symbol=sym,
        root_changed_symbol_id=sym_id,
        depth=depth,
        propagation_path=[sym_id],
        evidence=[
            EvidenceReference(
                evidence_type=EvidenceType.DIRECT_DIFF_MATCH,
                location=sym.location,
                description="Test evidence",
            )
        ],
        is_breaking=is_breaking,
        is_ui_affected=is_ui_affected,
        suggested_tests=[],
        severity=RiskLevel.LOW,
        confidence=confidence,
        affected_modules=modules or [":app"],
        related_features=[],
    )


class TestRiskEngine:
    """Validate severity classification, confidence calculation, and deterministic scoring."""

    def test_clean_workspace_produces_low_risk(self) -> None:
        engine = RiskEngine()
        assessment = engine.evaluate(findings=[], affected_modules=[], missing_test_count=0)
        assert assessment.level == RiskLevel.LOW
        assert assessment.score == 0.0
        assert assessment.confidence == ConfidenceLevel.VERIFIED
        assert len(assessment.reasons) == 1

    def test_breaking_change_elevates_to_critical_risk(self) -> None:
        engine = RiskEngine()
        finding = make_finding(
            "kt://MainActivity", "MainActivity", depth=0, is_breaking=True, is_ui_affected=True
        )
        assessment = engine.evaluate(
            findings=[finding], affected_modules=[":app"], missing_test_count=0
        )

        assert assessment.level == RiskLevel.CRITICAL
        assert assessment.score >= 25.0
        assert len(assessment.breaking_change_signals) >= 1
        assert "MainActivity" in assessment.breaking_change_signals[0]

    def test_ui_impact_elevates_to_high_risk(self) -> None:
        engine = RiskEngine()
        f1 = make_finding("kt://UserView", "UserView", depth=1, is_ui_affected=True)
        f2 = make_finding("kt://LoginScreen", "LoginScreen", depth=2, is_ui_affected=True)
        assessment = engine.evaluate(
            findings=[f1, f2], affected_modules=[":app"], missing_test_count=0
        )

        assert assessment.level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        assert any("UI component" in r for r in assessment.reasons)

    def test_cross_module_propagation_adds_risk_factor(self) -> None:
        engine = RiskEngine()
        f1 = make_finding("kt://CoreAuth", "CoreAuth", depth=0, modules=[":core"])
        f2 = make_finding(
            "kt://CheckoutView", "CheckoutView", depth=1, modules=[":feature:checkout"]
        )
        assessment = engine.evaluate(
            findings=[f1, f2],
            affected_modules=[":core", ":feature:checkout"],
            missing_test_count=1,
        )

        assert any("distinct modules" in r for r in assessment.reasons)
        assert any("No automated tests" in r for r in assessment.reasons)

    def test_confidence_degrades_to_lowest_link(self) -> None:
        engine = RiskEngine()
        f1 = make_finding("kt://S1", "S1", confidence=ConfidenceLevel.VERIFIED)
        f2 = make_finding("kt://S2", "S2", confidence=ConfidenceLevel.POSSIBLE)
        assessment = engine.evaluate(
            findings=[f1, f2], affected_modules=[":app"], missing_test_count=0
        )

        # Severity and confidence are strictly separated
        assert assessment.confidence == ConfidenceLevel.POSSIBLE
        assert assessment.level in {RiskLevel.LOW, RiskLevel.MEDIUM}
