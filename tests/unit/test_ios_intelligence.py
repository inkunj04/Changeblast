"""Unit tests for iOS engineering intelligence analyzer."""

from __future__ import annotations

from changeblast.analysis.mobile.ios import IOSIntelligenceAnalyzer
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
    file_path: str = "ios/Sources/App.swift",
    annotations: list[str] | None = None,
    is_entry_point: bool = False,
) -> SourceSymbol:
    return SourceSymbol(
        id=f"swift://{name}",
        name=name,
        qualified_name=name,
        kind=SymbolKind.CLASS if "Controller" in name or "View" in name else SymbolKind.METHOD,
        language=Language.SWIFT,
        visibility=Visibility.PUBLIC,
        location=SourceLocation(
            file_path=file_path, start_line=1, start_column=0, end_line=40, end_column=1
        ),
        annotations=annotations or [],
        is_entry_point=is_entry_point,
    )


def make_finding(sym: SourceSymbol) -> ImpactFinding:
    return ImpactFinding(
        finding_id="f_ios_test",
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
        affected_modules=[":ios"],
        related_features=[],
    )


class TestIOSIntelligenceAnalyzer:
    """Validate all 10 iOS architectural intelligence domains."""

    def test_viewcontroller_lifecycle_analysis(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("viewDidLoad", is_entry_point=True)
        finding = analyzer.enrich_finding(make_finding(sym))

        assert finding.platform == Platform.IOS
        assert finding.mobile_domain == MobileDomain.LIFECYCLE
        assert finding.potential_consequence is not None
        assert (
            "viewdidload" in finding.potential_consequence.lower()
            or "subviews" in finding.potential_consequence.lower()
        )
        assert any("loadViewIfNeeded" in t for t in finding.suggested_tests)

    def test_swiftui_state_observation(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("CheckoutView", annotations=["State", "Binding"])
        finding = analyzer.enrich_finding(make_finding(sym))

        assert finding.mobile_domain == MobileDomain.STATE_RECOMPOSITION
        assert finding.potential_consequence is not None
        assert (
            "swiftui" in finding.potential_consequence.lower()
            or "invalidation" in finding.potential_consequence.lower()
        )
        assert any("ViewInspector" in t for t in finding.suggested_tests)

    def test_navigationstack_and_routing(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("CheckoutCoordinator")
        content = "navigationPath.append(destination)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.NAVIGATION_DEEPLINK
        assert finding.potential_consequence is not None
        assert (
            "navigationpath" in finding.potential_consequence.lower()
            or "routing" in finding.potential_consequence.lower()
        )
        assert any("NavigationPath" in t for t in finding.suggested_tests)

    def test_privacy_and_permissions(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("requestCameraAccess")
        content = "AVCaptureDevice.requestAccess(for: .video)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.PERMISSIONS
        assert finding.potential_consequence is not None
        assert (
            "Info.plist" in finding.potential_consequence
            or "SIGABRT" in finding.potential_consequence
        )
        assert any("Info.plist" in t for t in finding.suggested_tests)

    def test_background_tasks_scheduler(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("scheduleAppRefresh")
        content = "BGTaskScheduler.shared.register(forTaskWithIdentifier: id)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.BACKGROUND_WORK
        assert finding.potential_consequence is not None
        assert (
            "0x8badf00d" in finding.potential_consequence
            or "watchdog" in finding.potential_consequence.lower()
        )
        assert any("BGTaskScheduler" in t or "LLDB" in t for t in finding.suggested_tests)

    def test_core_data_persistence(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("UserEntity", annotations=["Model"])
        content = "class UserEntity: NSManagedObject"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.PERSISTENCE
        assert finding.potential_consequence is not None
        assert (
            "Core Data" in finding.potential_consequence
            or "migration" in finding.potential_consequence.lower()
        )
        assert any("Core Data" in t for t in finding.suggested_tests)

    def test_keychain_services(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("saveAuthToken")
        content = "SecItemAdd(query as CFDictionary, nil)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.PERSISTENCE
        assert finding.potential_consequence is not None
        assert (
            "errSecItemNotFound" in finding.potential_consequence
            or "keychain" in finding.potential_consequence.lower()
        )
        assert any("Keychain" in t for t in finding.suggested_tests)

    def test_dependency_injection_swinject(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("AppContainer")
        content = "let container = Container(); container.register(Service.self)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.DEPENDENCY_INJECTION
        assert finding.potential_consequence is not None
        assert (
            "resolution" in finding.potential_consequence.lower()
            or "container" in finding.potential_consequence.lower()
        )
        assert any("Container" in t for t in finding.suggested_tests)

    def test_urlsession_networking(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("fetchProfile")
        content = "let (data, response) = try await URLSession.shared.data(from: url)"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.NETWORKING_API
        assert finding.potential_consequence is not None
        assert (
            "DecodingError" in finding.potential_consequence
            or "response" in finding.potential_consequence.lower()
        )
        assert any("URLProtocol" in t for t in finding.suggested_tests)

    def test_storekit_subscription_entitlements(self) -> None:
        analyzer = IOSIntelligenceAnalyzer()
        sym = make_sym("SubscriptionManager")
        content = "for await result in Transaction.updates"
        finding = analyzer.enrich_finding(make_finding(sym), file_content=content)

        assert finding.mobile_domain == MobileDomain.BILLING_SUBSCRIPTIONS
        assert finding.severity == RiskLevel.CRITICAL
        assert finding.potential_consequence is not None
        assert (
            "StoreKit" in finding.potential_consequence
            or "entitlement" in finding.potential_consequence.lower()
        )
        assert any("StoreKit" in t for t in finding.suggested_tests)
