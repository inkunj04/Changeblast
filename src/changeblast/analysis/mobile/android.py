"""Android engineering intelligence analyzer."""

from __future__ import annotations

from dataclasses import dataclass

from changeblast.models.common import MobileDomain, Platform, RiskLevel
from changeblast.models.finding import ImpactFinding
from changeblast.models.symbol import SourceSymbol


@dataclass(frozen=True)
class AndroidAssessment:
    """Classified mobile domain, severity recommendation, consequence, and recommended tests."""

    domain: MobileDomain
    severity: RiskLevel
    consequence: str
    recommended_tests: list[str]


class AndroidIntelligenceAnalyzer:
    """Analyzes Android-specific architectural relationships across lifecycle, compose,

    navigation, permissions, WorkManager, Room, Hilt, and billing.
    """

    def analyze_symbol(
        self,
        symbol: SourceSymbol,
        file_content: str | None = None,
    ) -> AndroidAssessment:
        """Classify Android symbol into architectural subdomain and determine potential failure modes."""
        name = symbol.name
        qname = symbol.qualified_name.lower()
        content = (file_content or "").lower()
        annotations = [a.lower() for a in symbol.annotations]

        # 1. Billing & Subscription Entitlements
        if any(
            k in qname or k in name.lower() or k in content
            for k in (
                "billingclient",
                "purchasesupdatedlistener",
                "queryproductdetails",
                "acknowledgepurchase",
                "billingflow",
            )
        ):
            return AndroidAssessment(
                domain=MobileDomain.BILLING_SUBSCRIPTIONS,
                severity=RiskLevel.CRITICAL,
                consequence="Entitlement loss or auto-refund: unacknowledged purchases are refunded after 3 days by Google Play. Billing response code mismatch can lock valid subscribers.",
                recommended_tests=[
                    "Google Play Billing test track purchase simulation",
                    "AcknowledgePurchase timeout and network retry test",
                    "Subscription status entitlement cache refresh test",
                ],
            )

        # 2. Manifest Configuration
        if "manifest" in qname or "manifest" in symbol.location.file_path.lower():
            return AndroidAssessment(
                domain=MobileDomain.MANIFEST_CONFIGURATION,
                severity=RiskLevel.HIGH,
                consequence="Component launch failure on Android 12+ if explicit android:exported is missing; security vulnerability exposing unexported components.",
                recommended_tests=[
                    "Package manager queryIntentActivities test",
                    "Manifest merger verification and export security check",
                ],
            )

        # 3. Runtime Permissions
        perm_keywords = (
            "permission",
            "checkselfpermission",
            "requestpermissions",
            "requestpermission",
            "post_notifications",
            "access_fine_location",
        )
        if any(k in qname or k in content for k in perm_keywords):
            return AndroidAssessment(
                domain=MobileDomain.PERMISSIONS,
                severity=RiskLevel.HIGH,
                consequence="SecurityException / crash on missing runtime permission check prior to hardware/location access; permanent denial without rationale flow.",
                recommended_tests=[
                    "GrantPermissionsRule automated permission granted/denied instrumentation tests",
                    "Permission rationale dialog dismissal edge-case test",
                ],
            )

        # 4. Background Services & WorkManager
        work_keywords = (
            "worker",
            "coroutineworker",
            "workmanager",
            "jobservice",
            "foregroundservice",
        )
        if any(k in qname or k in name.lower() for k in work_keywords):
            return AndroidAssessment(
                domain=MobileDomain.BACKGROUND_WORK,
                severity=RiskLevel.HIGH,
                consequence="ForegroundServiceStartNotAllowedException on background launch (Android 12+); WorkManager constraint cancellation under Doze mode.",
                recommended_tests=[
                    "WorkManager TestDriver testing constraint satisfaction with SynchronousExecutor",
                    "Periodic work reschedule and backoff policy test",
                ],
            )

        # 5. Room & DataStore Persistence
        db_keywords = ("dao", "entity", "database", "datastore", "preferences", "room")
        if any(k in qname or k in name.lower() for k in db_keywords) or any(
            a in ("entity", "dao", "database", "query", "insert") for a in annotations
        ):
            return AndroidAssessment(
                domain=MobileDomain.PERSISTENCE,
                severity=RiskLevel.HIGH,
                consequence="IllegalStateException: Room cannot verify data integrity (missing schema migration); DataStore disk I/O blocking main thread.",
                recommended_tests=[
                    "MigrationTestHelper automated Room schema migration test",
                    "In-memory Room database DAO transaction rollback test",
                ],
            )

        # 6. Dependency Injection (Hilt / Dagger)
        di_keywords = ("hilt", "dagger", "inject", "module", "provides", "binds", "entrypoint")
        if any(k in qname or k in name.lower() for k in di_keywords) or any(
            a in ("inject", "module", "provides", "binds", "androidentrypoint", "hiltandroidapp")
            for a in annotations
        ):
            return AndroidAssessment(
                domain=MobileDomain.DEPENDENCY_INJECTION,
                severity=RiskLevel.HIGH,
                consequence="UnsatisfiedDependencyException or runtime injection crash at Android component entry point; scoped ViewModel memory leak.",
                recommended_tests=[
                    "HiltAndroidRule component integration test",
                    "Dagger compile-time component validation test",
                ],
            )

        # 7. Navigation & Deep Links
        nav_keywords = ("navhost", "navcontroller", "deeplink", "navgraph", "navigation")
        if any(k in qname or k in name.lower() for k in nav_keywords):
            return AndroidAssessment(
                domain=MobileDomain.NAVIGATION_DEEPLINK,
                severity=RiskLevel.HIGH,
                consequence="Broken deep link entry point or missing navigation route arguments causing runtime IllegalArgumentException; backstack corruption.",
                recommended_tests=[
                    "TestNavHostController destination assertions",
                    "Deep link ADB intent dispatch test (am start -a VIEW -d ...)",
                ],
            )

        # 8. Jetpack Compose State & Recomposition
        if (
            "composable" in annotations
            or "composable" in name.lower()
            or any(
                k in content
                for k in ("remember", "mutablestateof", "collectasstate", "derivedstateof")
            )
        ):
            return AndroidAssessment(
                domain=MobileDomain.STATE_RECOMPOSITION,
                severity=RiskLevel.HIGH if symbol.is_entry_point else RiskLevel.MEDIUM,
                consequence="Unbounded recomposition loops causing UI frame drops and battery drain; state loss on recomposition if rememberSaveable is omitted.",
                recommended_tests=[
                    "ComposeTestRule assertIsDisplayed and recomposition count benchmark",
                    "Configuration change (screen rotation) state preservation test",
                ],
            )

        # 9. Activity & Fragment Lifecycle
        lifecycle_keywords = ("activity", "fragment", "dialogfragment", "lifecycle")
        lifecycle_methods = (
            "oncreate",
            "onresume",
            "onpause",
            "ondestroy",
            "onviewcreated",
            "ondestroyview",
        )
        if any(k in name.lower() for k in lifecycle_keywords) or name.lower() in lifecycle_methods:
            return AndroidAssessment(
                domain=MobileDomain.LIFECYCLE,
                severity=RiskLevel.HIGH if symbol.is_entry_point else RiskLevel.MEDIUM,
                consequence="Fragment view binding memory leak holding Activity context beyond onDestroyView; IllegalStateException accessing view after onDestroy.",
                recommended_tests=[
                    "FragmentScenario/ActivityScenario lifecycle state transition tests (moveToState(State.DESTROYED))",
                    "Process death and recreation simulation test",
                ],
            )

        # 10. API & Networking
        net_keywords = ("retrofit", "okhttp", "ktor", "api", "endpoint", "client")
        if any(k in qname or k in name.lower() for k in net_keywords) or any(
            a in ("get", "post", "put", "delete", "headers") for a in annotations
        ):
            return AndroidAssessment(
                domain=MobileDomain.NETWORKING_API,
                severity=RiskLevel.MEDIUM,
                consequence="HTTP 4xx/5xx payload deserialization crash on altered JSON response structure; NetworkOnMainThreadException.",
                recommended_tests=[
                    "MockWebServer API contract round-trip serialization tests",
                    "Network timeout and offline error handling test",
                ],
            )

        # Default General Android
        return AndroidAssessment(
            domain=MobileDomain.GENERAL,
            severity=RiskLevel.LOW,
            consequence="Potential logic defect in internal Android business component.",
            recommended_tests=["Component unit test covering modified methods"],
        )

    def enrich_finding(
        self,
        finding: ImpactFinding,
        file_content: str | None = None,
    ) -> ImpactFinding:
        """Enrich finding with Android-specific mobile domain, consequences, and tests."""
        assessment = self.analyze_symbol(finding.target_symbol, file_content)

        # Merge tests
        tests = list(finding.suggested_tests)
        for t in assessment.recommended_tests:
            if t not in tests:
                tests.append(t)

        # Severity should not downgrade if already higher
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
                "platform": Platform.ANDROID,
                "mobile_domain": assessment.domain,
                "potential_consequence": assessment.consequence,
                "suggested_tests": tests,
                "severity": new_sev,
            }
        )
