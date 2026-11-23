# iOS Architectural Heuristics

ChangeBlast analyzes 10 native iOS architectural domains to detect concrete mobile failure modes:

| Domain | Key Indicators & Patterns | Potential Failure Consequence | Recommended Test Types |
| :--- | :--- | :--- | :--- |
| **Lifecycle** | `viewDidLoad`, `viewWillAppear`, `viewDidDisappear`, `UIViewController`, `loadView` | Accessing subviews before layout pass, unreleased retained delegates causing memory leaks on dismissal. | `loadViewIfNeeded()`, XCTest UI test |
| **State Observation** | `@State`, `@Binding`, `@Observable`, `@ObservedObject`, `@StateObject`, `View` body | Excessive SwiftUI view invalidations, recreation of `@StateObject` during parent redraws. | `ViewInspector`, SwiftUI snapshot tests |
| **Navigation & Routing** | `NavigationStack`, `NavigationPath`, `navigationDestination`, `onOpenURL` | Corrupted navigation path causing invalid destination view lookup or unhandled universal link routing. | `NavigationPath` state tests, deep link XCTest |
| **Permissions & Privacy** | `AVCaptureDevice.requestAccess`, `CLLocationManager`, `UNUserNotificationCenter` | App crash (`SIGABRT`) due to missing `NSCameraUsageDescription` or `NSLocationWhenInUseUsageDescription` in Info.plist. | Plist linting, UI permission flow tests |
| **Background Tasks** | `BGTaskScheduler`, `BGAppRefreshTask`, `BGProcessingTask`, `beginBackgroundTask` | Watchdog termination (`0x8badf00d`) for uncalled `setTaskCompleted(success:)` before expiration handler triggers. | `BGTaskScheduler` LLDB simulation |
| **Persistence** | `NSManagedObject`, `NSManagedObjectContext`, `NSPersistentContainer`, `Model` (SwiftData) | Core Data / SwiftData migration crashes due to unmapped model changes, merge conflicts in background contexts. | In-memory `NSPersistentContainer` migration tests |
| **Keychain Services** | `SecItemAdd`, `SecItemCopyMatching`, `SecItemDelete`, `kSecClassGenericPassword` | Unhandled `errSecItemNotFound` (-25300) or `errSecAuthFailed` causing authentication failure loops. | Mock Keychain service tests |
| **Dependency Injection** | `Container`, `Swinject`, `Factory`, `resolve`, `@Injected` | Unresolvable registered services resulting in fatal force-unwrap nil crashes at launch. | Container registration validation tests |
| **Networking & APIs** | `URLSession`, `URLSessionDataTask`, `async/await data(from:)`, `Decodable` | `DecodingError.keyNotFound` or `.typeMismatch` on modified API models, unhandled HTTP status codes. | `URLProtocol` mock stubbing |
| **StoreKit & Subscriptions**| `StoreKit 2`, `Product.purchase()`, `Transaction.updates`, `Transaction.finish()` | Unfinished transactions stuck in queue, entitlement loss due to unverified transaction cryptoseals. | StoreKit Test Configuration (`.storekit`) |
