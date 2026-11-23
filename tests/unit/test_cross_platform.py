"""Unit tests for CrossPlatformCorrelator."""

from __future__ import annotations

from changeblast.analysis.mobile.cross_platform import CrossPlatformCorrelator
from changeblast.models.common import (
    ConfidenceLevel,
    EvidenceType,
    Language,
    MobileDomain,
    Platform,
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
    lang: Language,
    features: list[str] | None = None,
    signature: str | None = None,
    annotations: list[str] | None = None,
    is_ui: bool = False,
) -> ImpactFinding:
    loc = SourceLocation(
        file_path="src/App.kt" if lang == Language.KOTLIN else "src/App.swift",
        start_line=1,
        start_column=0,
        end_line=20,
        end_column=1,
    )
    sym = SourceSymbol(
        id=sym_id,
        name=name,
        qualified_name=f"app.{name}",
        kind=SymbolKind.CLASS if is_ui else SymbolKind.METHOD,
        language=lang,
        visibility=Visibility.PUBLIC,
        location=loc,
        signature=signature,
        annotations=annotations or [],
        is_entry_point=is_ui,
    )
    return ImpactFinding(
        finding_id=f"f_{name}",
        target_symbol=sym,
        root_changed_symbol_id=sym.id,
        depth=0,
        propagation_path=[sym.id],
        evidence=[
            EvidenceReference(
                evidence_type=EvidenceType.DIRECT_DIFF_MATCH, location=loc, description="Match"
            )
        ],
        is_breaking=False,
        is_ui_affected=is_ui,
        suggested_tests=[],
        severity=RiskLevel.MEDIUM,
        confidence=ConfidenceLevel.VERIFIED,
        affected_modules=[":app"],
        related_features=features or [],
        platform=Platform.ANDROID if lang == Language.KOTLIN else Platform.IOS,
        mobile_domain=MobileDomain.GENERAL,
    )


class TestCrossPlatformCorrelator:
    """Validate cross-platform feature correlation and behavioral divergence disclosures."""

    def test_api_contract_correlation(self) -> None:
        correlator = CrossPlatformCorrelator()
        # Both reference "/api/v1/checkout"
        a_finding = make_finding(
            "kt://CheckoutApi",
            "CheckoutApi",
            Language.KOTLIN,
            annotations=['@POST("/api/v1/checkout")'],
        )
        i_finding = make_finding(
            "swift://CheckoutClient",
            "CheckoutClient",
            Language.SWIFT,
            signature='func checkout() async -> URL { "/api/v1/checkout" }',
        )

        correlations = correlator.correlate([a_finding], [i_finding])
        assert len(correlations) == 1
        c = correlations[0]
        assert c.correlation_type == "api_contract"
        assert c.confidence == ConfidenceLevel.VERIFIED
        assert "api_v1_checkout" in c.feature_name or "checkout" in c.feature_name
        # Discloses divergence warning
        assert "BEHAVIORAL DIVERGENCE WARNING" in c.notes

    def test_screen_flow_correlation(self) -> None:
        correlator = CrossPlatformCorrelator()
        # Android CheckoutActivity vs iOS CheckoutViewController
        a_finding = make_finding(
            "kt://CheckoutActivity", "CheckoutActivity", Language.KOTLIN, is_ui=True
        )
        i_finding = make_finding(
            "swift://CheckoutViewController", "CheckoutViewController", Language.SWIFT, is_ui=True
        )

        correlations = correlator.correlate([a_finding], [i_finding])
        assert len(correlations) == 1
        c = correlations[0]
        assert c.correlation_type == "screen_flow"
        assert c.feature_name == "Checkout"
        assert c.confidence == ConfidenceLevel.STRONG_INFERENCE
        assert "BEHAVIORAL DIVERGENCE WARNING" in c.notes

    def test_feature_mapping_correlation(self) -> None:
        correlator = CrossPlatformCorrelator()
        # Both reside in "billing" feature domain
        a_finding = make_finding(
            "kt://BillingHelper", "BillingHelper", Language.KOTLIN, features=["billing"]
        )
        i_finding = make_finding(
            "swift://ReceiptValidator", "ReceiptValidator", Language.SWIFT, features=["billing"]
        )

        correlations = correlator.correlate([a_finding], [i_finding])
        assert len(correlations) == 1
        c = correlations[0]
        assert c.correlation_type == "feature_mapping"
        assert c.feature_name == "billing"
        assert c.confidence == ConfidenceLevel.STRONG_INFERENCE

    def test_dissimilar_features_do_not_falsely_correlate(self) -> None:
        correlator = CrossPlatformCorrelator()
        # Auth on Android vs Cart on iOS
        a_finding = make_finding(
            "kt://LoginScreen", "LoginScreen", Language.KOTLIN, features=["auth"], is_ui=True
        )
        i_finding = make_finding(
            "swift://CartView", "CartView", Language.SWIFT, features=["cart"], is_ui=True
        )

        correlations = correlator.correlate([a_finding], [i_finding])
        assert len(correlations) == 0
