# ADR 0004: Phase 4 Mobile Engineering Intelligence & Cross-Platform Correlation

## Status
**Accepted** (2026-11-23)

## Context
Mobile engineering requires domain-specific static intelligence beyond generic call-graph reachability. Changes to lifecycle methods, state containers, runtime permissions, WorkManager workers, StoreKit subscriptions, or Room migrations carry concrete mobile-specific failure modes (e.g. Activity recreation crashes, recomposition loops, auto-refunds on unacknowledged billing). Furthermore, in mixed repositories containing both Android and iOS implementations of shared features, developers require cross-platform correlation while strictly disclosing behavioral divergence.

## Decisions

### 1. Android Engineering Intelligence Analyzer (`AndroidIntelligenceAnalyzer`)
- Implemented in `changeblast.analysis.mobile.android`:
  - Classifies symbols into 10 mobile domains:
    1. **Lifecycle**: Activity/Fragment lifecycle state machines, view binding leaks, and configuration change state retention.
    2. **State & Recomposition**: Jetpack Compose `@Composable`, `rememberSaveable`, state hoisting, and recomposition loops.
    3. **Navigation & Deep Links**: `NavHost`, `NavController`, `NavDeepLink`, and deep link argument verification.
    4. **Runtime Permissions**: Dangerous permissions, `checkSelfPermission`, `ActivityResultContracts.RequestPermission`.
    5. **Manifest Configuration**: Component export status (`android:exported`), intent-filters, service declarations.
    6. **Background Work**: `CoroutineWorker`, `WorkManager`, Doze mode constraints, `ForegroundService`.
    7. **Persistence**: Room `@Entity`, `@Dao`, schema migrations, DataStore main-thread blocking.
    8. **Dependency Injection**: Hilt/Dagger `@AndroidEntryPoint`, `@Module`, scoped component leaks.
    9. **Networking & API**: Retrofit, OkHttp, Ktor deserialization safety, network-on-main-thread protection.
    10. **Billing & Subscriptions**: Google Play `BillingClient`, `acknowledgePurchase` 3-day auto-refund protection.
  - Enriches findings with concrete runtime failure modes (`potential_consequence`) and dedicated regression test strategies.

### 2. iOS Engineering Intelligence Analyzer (`IOSIntelligenceAnalyzer`)
- Implemented in `changeblast.analysis.mobile.ios`:
  - Classifies symbols into 10 mobile domains:
    1. **Lifecycle**: `UIViewController` lifecycle (`viewDidLoad`, `viewDidLayoutSubviews`), `ScenePhase` background transitions.
    2. **State & Observation**: SwiftUI `@State`, `@Binding`, `@ObservedObject`, `@EnvironmentObject` hierarchy crashes, `@Observable`.
    3. **Navigation & Routing**: `NavigationStack`, `NavigationPath` Hashable destination registration, Universal Links.
    4. **Permissions & Privacy**: `Info.plist` privacy keys audit preventing instant SIGABRT crashes on hardware access.
    5. **Background Tasks**: `BGTaskScheduler`, `BGAppRefreshTask` 0x8badf00d watchdog termination.
    6. **Persistence**: Core Data `NSPersistentStoreIncompatibleVersionHashError`, SwiftData `@Model`, background context safety.
    7. **Keychain**: `SecItem` operations, device lock state accessibility attributes (`kSecAttrAccessibleWhenUnlocked`).
    8. **Dependency Injection**: Swinject, Needle, Factory container resolution crashes.
    9. **Networking & API**: `URLSession`, async/await, `Codable` payload schema regression.
    10. **StoreKit & Subscriptions**: StoreKit 2 `Product.purchase()`, `Transaction.updates` listener, entitlement locking.
  - Enriches findings with concrete runtime consequences and test recommendations.

### 3. Evidence-Backed Cross-Platform Correlator (`CrossPlatformCorrelator`)
- Identifies corresponding features across native Android and iOS components based on:
  - **API Contract Matching**: Identical API endpoint URI strings referenced in network calls/annotations.
  - **Screen Flow Matching**: Matching UI view controller / screen stems.
  - **Feature Domain Mapping**: Shared architectural domain folders (e.g. `checkout`, `billing`, `auth`).
  - **Shared Behavior**: Matching domain model entities.
- **Mandatory Behavioral Divergence Disclosure**: Explicitly discloses:
  > *"BEHAVIORAL DIVERGENCE WARNING: Android and iOS implementations differ fundamentally in lifecycle management, concurrency dispatch, and OS platform contracts. Never assume identically named components behave identically. Verify both platforms with dedicated native tests."*

### 4. Static Analysis Disclosures
- Explicitly discloses limitations: dynamic dispatch, runtime string URL evaluation, OS scheduler memory pressure, server-driven UI, and external server-to-server webhook validation.

## Consequences
- Accurate, mobile-first intelligence without running compilers or emulators.
- High precision on mobile architectural patterns while strictly read-only.
