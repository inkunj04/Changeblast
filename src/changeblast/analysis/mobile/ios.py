"""iOS engineering intelligence analyzer."""

from __future__ import annotations

from dataclasses import dataclass

from changeblast.models.common import MobileDomain, Platform, RiskLevel
from changeblast.models.finding import ImpactFinding
from changeblast.models.symbol import SourceSymbol


@dataclass(frozen=True)
class IOSAssessment:
    """Classified mobile domain, severity recommendation, consequence, and recommended tests."""

    domain: MobileDomain
    severity: RiskLevel
    consequence: str
    recommended_tests: list[str]


class IOSIntelligenceAnalyzer:
    """Analyzes iOS-specific architectural relationships across UIViewController lifecycle,

    SwiftUI state observation, NavigationStack, StoreKit, Core Data, Keychain, and background tasks.
    """

    def analyze_symbol(
        self,
        symbol: SourceSymbol,
        file_content: str | None = None,
    ) -> IOSAssessment:
        """Classify Swift symbol into architectural subdomain and determine potential failure modes."""
        name = symbol.name
        name_lower = name.lower()
        content = (file_content or "").lower()
        annotations = [a.lower() for a in symbol.annotations]

        # 1. StoreKit & Subscription Entitlements
        store_keywords = (
            "storekit",
            "product.purchase",
            "currententitlements",
            "transaction.updates",
            "storekit2",
        )
        if any(k in name_lower or k in content for k in store_keywords):
            return IOSAssessment(
                domain=MobileDomain.BILLING_SUBSCRIPTIONS,
                severity=RiskLevel.CRITICAL,
                consequence="Unfinished transaction causing StoreKit payment queue buildup; entitlement lock where valid in-app purchase is ungranted.",
                recommended_tests=[
                    "StoreKit Test Configuration (.storekit) automated test",
                    "Transaction.updates listener simulation on app launch",
                    "Subscription renewal and grace period handling test",
                ],
            )

        # 2. Keychain & Secure Enclave
        keychain_keywords = (
            "secitemadd",
            "secitemcopymatching",
            "secitemupdate",
            "ksecclass",
            "keychain",
        )
        if any(k in name_lower or k in content for k in keychain_keywords):
            return IOSAssessment(
                domain=MobileDomain.PERSISTENCE,
                severity=RiskLevel.HIGH,
                consequence="errSecItemNotFound / errSecAuthFailed lockout; item inaccessible while device is locked if kSecAttrAccessibleWhenUnlocked is omitted.",
                recommended_tests=[
                    "Simulator Keychain mock credential storage test",
                    "Device lock / biometric auth cancellation fallback test",
                ],
            )

        # 3. Core Data & SwiftData Persistence
        cd_keywords = (
            "nsmanagedobject",
            "persistentcontainer",
            "managedobjectcontext",
            "swiftdata",
            "fetchrequest",
        )
        if any(k in name_lower or k in content for k in cd_keywords) or any(
            a in ("model", "fetchrequest") for a in annotations
        ):
            return IOSAssessment(
                domain=MobileDomain.PERSISTENCE,
                severity=RiskLevel.HIGH,
                consequence="Core Data migration failure with NSPersistentStoreIncompatibleVersionHashError; cross-thread NSManagedObject concurrency crash.",
                recommended_tests=[
                    "Core Data automated migration test with in-memory SQLite store",
                    "NSPersistentContainer concurrency and background context test",
                ],
            )

        # 4. Privacy & Runtime Permissions
        perm_keywords = (
            "avcapturedevice",
            "cllocationmanager",
            "phphotolibrary",
            "unusernotificationcenter",
            "requestauthorization",
        )
        if any(k in name_lower or k in content for k in perm_keywords):
            return IOSAssessment(
                domain=MobileDomain.PERMISSIONS,
                severity=RiskLevel.HIGH,
                consequence="Missing Info.plist privacy usage description string (e.g. NSCameraUsageDescription) triggers instant iOS SIGABRT crash on access.",
                recommended_tests=[
                    "Info.plist privacy keys audit and permission denial fallback test",
                    "Location accuracy degradation edge-case test",
                ],
            )

        # 5. Background Tasks
        bg_keywords = (
            "bgtaskscheduler",
            "bgapprefreshtask",
            "bgprocessingtask",
            "beginbackgroundtask",
        )
        if any(k in name_lower or k in content for k in bg_keywords):
            return IOSAssessment(
                domain=MobileDomain.BACKGROUND_WORK,
                severity=RiskLevel.HIGH,
                consequence="App termination with 0x8badf00d watchdog crash if background task expires before calling setTaskCompleted.",
                recommended_tests=[
                    "LLDB _simulateLaunchForTaskWithIdentifier test",
                    "Background task completion expiration timeout simulation",
                ],
            )

        # 6. Dependency Injection (Swinject / Needle / Factory)
        di_keywords = ("swinject", "needle", "resolver", "factory", "container")
        if any(k in name_lower or k in content for k in di_keywords) or any(
            a in ("injected", "injectedobject") for a in annotations
        ):
            return IOSAssessment(
                domain=MobileDomain.DEPENDENCY_INJECTION,
                severity=RiskLevel.HIGH,
                consequence="Fatal resolution crash: Dependency not registered in container; factory cyclic dependency deadlock.",
                recommended_tests=[
                    "Container registration test asserting all graph dependencies resolve",
                    "Mock container test suite",
                ],
            )

        # 7. NavigationStack, Routing & Deep Links
        nav_keywords = (
            "navigationstack",
            "navigationdestination",
            "navigationpath",
            "coordinator",
            "router",
            "onopenurl",
            "universal links",
        )
        if any(k in name_lower or k in content for k in nav_keywords):
            return IOSAssessment(
                domain=MobileDomain.NAVIGATION_DEEPLINK,
                severity=RiskLevel.HIGH,
                consequence="NavigationPath crash on unhandled Hashable destination; broken Universal Link routing dropping user on fallback view.",
                recommended_tests=[
                    "NavigationPath push/pop integration test",
                    "xcrun simctl openurl deep link test",
                ],
            )

        # 8. SwiftUI State & Observation
        state_annotations = (
            "state",
            "binding",
            "observedobject",
            "stateobject",
            "environmentobject",
            "environment",
            "published",
            "observable",
        )
        if any(a in state_annotations for a in annotations) or "swiftui" in content:
            return IOSAssessment(
                domain=MobileDomain.STATE_RECOMPOSITION,
                severity=RiskLevel.HIGH if symbol.is_entry_point else RiskLevel.MEDIUM,
                consequence="SwiftUI fatal error on missing EnvironmentObject; infinite view invalidation update loop; state loss across sheet dismissals.",
                recommended_tests=[
                    "ViewInspector state mutation tests",
                    "SwiftUI view preview regression test suite",
                ],
            )

        # 9. UIViewController & App Lifecycle
        vc_keywords = ("viewcontroller", "navigationcontroller", "tableviewcontroller")
        vc_methods = (
            "viewdidload",
            "viewwillappear",
            "viewdidappear",
            "viewwilldisappear",
            "viewdiddisappear",
            "loadview",
            "viewdidlayoutsubviews",
        )
        if any(k in name_lower for k in vc_keywords) or name_lower in vc_methods:
            return IOSAssessment(
                domain=MobileDomain.LIFECYCLE,
                severity=RiskLevel.HIGH if symbol.is_entry_point else RiskLevel.MEDIUM,
                consequence="Accessing subviews before viewDidLoad causes crash; viewDidLayoutSubviews layout recursion; notification observer leaks.",
                recommended_tests=[
                    "XCTest loadViewIfNeeded lifecycle simulation",
                    "Snapshot test across view transitions and dark mode toggle",
                ],
            )

        # 10. Networking & APIs
        net_keywords = ("urlsession", "urlrequest", "alamofire", "jsondecoder", "codable")
        if any(k in name_lower or k in content for k in net_keywords):
            return IOSAssessment(
                domain=MobileDomain.NETWORKING_API,
                severity=RiskLevel.MEDIUM,
                consequence="DecodingError.keyNotFound / typeMismatch runtime crash on modified response payload; ATS exception requirement.",
                recommended_tests=[
                    "URLProtocol network stubbing test",
                    "Codable schema regression test",
                ],
            )

        # Default General iOS
        return IOSAssessment(
            domain=MobileDomain.GENERAL,
            severity=RiskLevel.LOW,
            consequence="Potential logic defect in internal iOS component.",
            recommended_tests=["Unit test covering modified Swift functions"],
        )

    def enrich_finding(
        self,
        finding: ImpactFinding,
        file_content: str | None = None,
    ) -> ImpactFinding:
        """Enrich finding with iOS-specific mobile domain, consequences, and tests."""
        assessment = self.analyze_symbol(finding.target_symbol, file_content)

        tests = list(finding.suggested_tests)
        for t in assessment.recommended_tests:
            if t not in tests:
                tests.append(t)

        severities = {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }
        current_sev = finding.severity
        new_sev = current_sev
        if severities.get(assessment.severity, 1) > severities.get(current_sev, 1):
            new_sev = assessment.severity

        return finding.model_copy(
            update={
                "platform": Platform.IOS,
                "mobile_domain": assessment.domain,
                "potential_consequence": assessment.consequence,
                "suggested_tests": tests,
                "severity": new_sev,
            }
        )
