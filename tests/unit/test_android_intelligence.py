"""Unit tests for Android engineering intelligence analyzer."""

from __future__ import annotations

from changeblast.analysis.mobile.android import AndroidIntelligenceAnalyzer
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


def make_sym(
    name: str,
    qname: str,
    file_path: str = "app/src/main/kotlin/App.kt",
    annotations: list[str] | None = None,
    is_entry_point: bool = False,
) -> SourceSymbol:
    return SourceSymbol(
        id=f"kt://{qname}",
        name=name,
        qualified_name=qname,
        kind=SymbolKind.CLASS if "Activity" in name or "Screen" in name else SymbolKind.METHOD,
        language=Language.KOTLIN,
        visibility=Visibility.PUBLIC,
        location=SourceLocation(
            file_path=file_path, start_line=10, start_column=0, end_line=50, end_column=1
        ),
        annotations=annotations or [],
        is_entry_point=is_entry_point,
    )


def make_finding(sym: SourceSymbol) -> ImpactFinding:
    return ImpactFinding(
        finding_id="f_test",
        target_symbol=sym,
        root_changed_symbol_id=sym.id,
        depth=0,
        propagation_path=[sym.id],
        evidence=[
            EvidenceReference(
                evidence_type=EvidenceType.DIRECT_DIFF_MATCH,
                location=sym.location,
                description="Test diff match",
            )
        ],
        is_breaking=False,
        is_ui_affected=sym.is_entry_point,
        suggested_tests=[],
        severity=RiskLevel.LOW,
        confidence=ConfidenceLevel.VERIFIED,
        affected_modules=[":app"],
        related_features=[],
    )


class TestAndroidIntelligenceAnalyzer:
    """Validate all 10 Android architectural intelligence domains."""

    def test_activity_lifecycle_analysis(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym("onCreate", "com.example.app.MainActivity.onCreate", is_entry_point=True)
        finding = analyzer.enrich_finding(make_finding(sym))

        assert finding.platform == Platform.ANDROID
        assert finding.mobile_domain == MobileDomain.LIFECYCLE
        assert finding.severity in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        assert finding.potential_consequence is not None
        assert (
            "binding" in finding.potential_consequence.lower()
            or "state" in finding.potential_consequence.lower()
        )
        assert any("ActivityScenario" in t for t in finding.suggested_tests)

    def test_compose_state_recomposition_analysis(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym(
            "CheckoutScreen", "com.example.app.CheckoutScreen", annotations=["Composable"]
        )
        content = "val state = remember { mutableStateOf(0) }"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.STATE_RECOMPOSITION
        assert finding.potential_consequence is not None
        assert "recomposition" in finding.potential_consequence.lower()
        assert any("ComposeTestRule" in t for t in finding.suggested_tests)

    def test_navigation_and_deeplink_analysis(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym("AppNavHost", "com.example.app.navigation.AppNavHost")
        content = "navController.navigate('checkout')"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.NAVIGATION_DEEPLINK
        assert finding.potential_consequence is not None
        assert (
            "deep link" in finding.potential_consequence.lower()
            or "navigation" in finding.potential_consequence.lower()
        )
        assert any("TestNavHostController" in t for t in finding.suggested_tests)

    def test_runtime_permissions_analysis(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym("requestCamera", "com.example.app.CameraManager.requestCamera")
        content = "checkSelfPermission(Manifest.permission.CAMERA)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.PERMISSIONS
        assert finding.potential_consequence is not None
        assert "SecurityException" in finding.potential_consequence
        assert any("GrantPermissionsRule" in t for t in finding.suggested_tests)

    def test_manifest_configuration_analysis(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym(
            "AndroidManifest",
            "manifest.AndroidManifest",
            file_path="app/src/main/AndroidManifest.xml",
        )
        finding = analyzer.enrich_finding(make_finding(sym))

        assert finding.mobile_domain == MobileDomain.MANIFEST_CONFIGURATION
        assert finding.potential_consequence is not None
        assert "exported" in finding.potential_consequence.lower()
        assert any("queryIntentActivities" in t for t in finding.suggested_tests)

    def test_workmanager_and_background_work(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym("SyncWorker", "com.example.app.SyncWorker")
        content = "class SyncWorker : CoroutineWorker(appContext, params)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.BACKGROUND_WORK
        assert finding.potential_consequence is not None
        assert (
            "WorkManager" in finding.potential_consequence
            or "ForegroundService" in finding.potential_consequence
        )
        assert any("WorkManager TestDriver" in t for t in finding.suggested_tests)

    def test_room_database_and_persistence(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym("UserDao", "com.example.app.db.UserDao", annotations=["Dao"])
        finding = analyzer.enrich_finding(make_finding(sym))

        assert finding.mobile_domain == MobileDomain.PERSISTENCE
        assert finding.potential_consequence is not None
        assert (
            "Room" in finding.potential_consequence
            or "migration" in finding.potential_consequence.lower()
        )
        assert any("MigrationTestHelper" in t for t in finding.suggested_tests)

    def test_hilt_dependency_injection(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym(
            "AuthModule", "com.example.app.di.AuthModule", annotations=["Module", "Provides"]
        )
        finding = analyzer.enrich_finding(make_finding(sym))

        assert finding.mobile_domain == MobileDomain.DEPENDENCY_INJECTION
        assert finding.potential_consequence is not None
        assert (
            "UnsatisfiedDependencyException" in finding.potential_consequence
            or "injection" in finding.potential_consequence.lower()
        )
        assert any("HiltAndroidRule" in t for t in finding.suggested_tests)

    def test_retrofit_api_networking(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym(
            "fetchOrders", "com.example.app.api.OrderApi.fetchOrders", annotations=["GET"]
        )
        finding = analyzer.enrich_finding(make_finding(sym))

        assert finding.mobile_domain == MobileDomain.NETWORKING_API
        assert finding.potential_consequence is not None
        assert (
            "deserialization" in finding.potential_consequence.lower()
            or "http" in finding.potential_consequence.lower()
        )
        assert any("MockWebServer" in t for t in finding.suggested_tests)

    def test_google_play_billing_entitlements(self) -> None:
        analyzer = AndroidIntelligenceAnalyzer()
        sym = make_sym("BillingManager", "com.example.app.billing.BillingManager")
        content = "billingClient.acknowledgePurchase(params)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.BILLING_SUBSCRIPTIONS
        assert finding.severity == RiskLevel.CRITICAL
        assert finding.potential_consequence is not None
        assert (
            "auto-refund" in finding.potential_consequence.lower()
            or "unacknowledged" in finding.potential_consequence.lower()
        )
        assert any("Billing" in t for t in finding.suggested_tests)
