# Android Architectural Heuristics

ChangeBlast analyzes 10 native Android architectural domains to detect concrete mobile failure modes:

| Domain | Key Indicators & Patterns | Potential Failure Consequence | Recommended Test Types |
| :--- | :--- | :--- | :--- |
| **Lifecycle** | `onCreate`, `onDestroy`, `onStart`, `Fragment`, `Activity`, `viewBinding` | View binding memory leaks after `onDestroyView`, state loss across configuration changes. | `ActivityScenarioRule`, `FragmentScenario` |
| **State Recomposition** | `@Composable`, `remember`, `mutableStateOf`, `derivedStateOf`, `SnapshotState` | Unstable parameter recomposition loops, redundant UI frame redraws, dropped animation frames. | `createComposeRule`, `ComposeTestRule` |
| **Navigation & Deep Links** | `NavHost`, `navController.navigate`, `intent-filter`, `data android:scheme` | Broken deep link routing, missing destination arguments causing runtime bundle deserialization crashes. | `TestNavHostController` |
| **Runtime Permissions** | `checkSelfPermission`, `requestPermissions`, `registerForActivityResult`, `CAMERA` | Uncaught `SecurityException` crashes when calling hardware or privacy APIs without prior grant. | `GrantPermissionsRule` |
| **Manifest Config** | `AndroidManifest.xml`, `android:exported`, `<activity>`, `<service>` | Inadvertently exported components allowing malicious intent execution, launchMode task stack corruption. | `PackageManager` tests, Intent filter verification |
| **Background Work** | `CoroutineWorker`, `Worker`, `WorkManager`, `ForegroundService`, `enqueueUniqueWork` | Expedited job failures, notification channel omissions on Android 13+, work cancellation during battery saver. | `WorkManager TestDriver` |
| **Persistence** | `@Entity`, `@Dao`, `@Database`, `RoomDatabase`, `DataStore` | Destructive schema migrations wiping SQLite tables, missing `@TypeConverter` crashes. | `MigrationTestHelper` |
| **Dependency Injection** | `@HiltAndroidApp`, `@AndroidEntryPoint`, `@Module`, `@Provides`, `@Inject` | `UnsatisfiedDependencyException` at runtime or app launch failure due to incorrect scope installation. | `HiltAndroidRule` |
| **Networking & APIs** | `@GET`, `@POST`, `Retrofit`, `OkHttpClient`, `HttpClient` (Ktor) | JSON deserialization crashes due to changed field types, unhandled HTTP 4xx/5xx responses. | `MockWebServer` |
| **Billing & Entitlements** | `BillingClient`, `acknowledgePurchase`, `queryProductDetails`, `PurchasesUpdatedListener` | Auto-refund of purchases after 3 days if unacknowledged, granting items without verifying purchase token. | Google Play Billing Testing / Fake Billing Client |
