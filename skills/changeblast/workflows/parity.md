# Workflow: Cross-Platform Parity Verification (`/changeblast parity`)

Inspects feature correspondences and architectural parity between Android (Kotlin, Java) and iOS (Swift) implementations.

## Step-by-Step Execution

1. **Execute Parity Analysis**:
   ```bash
   changeblast parity --format json
   ```

2. **Interpret Correlations**:
   - Each correlation links an Android symbol to an iOS symbol via verifiable evidence:
     - `api_contract`: Identical backend REST / GraphQL route strings in annotations or signatures.
     - `screen_flow`: Corresponding navigation coordinates or coordinator routes.
     - `feature_mapping`: Matching business domain models and use cases.
   - Confidence: `STRONG_INFERENCE` or `POSSIBLE`.

3. **Behavioral Divergence Principles**:
   - **CRITICAL**: Never assume Android and iOS implementations behave identically just because names match!
   - Highlight platform architectural divergences:
     - Android lifecycle vs. iOS lifecycle (e.g. Activity recreation on rotation vs. UIViewController persistence).
     - Android Coroutines/WorkManager vs. Swift Concurrency/BGTaskScheduler.
     - Jetpack Compose snapshot state vs. SwiftUI `@Observable` invalidation.
     - Google Play Billing purchase acknowledgment vs. StoreKit 2 transaction verification.

4. **Present Parity Report**:
   - Feature Correlation Table (Feature, Android Component, iOS Component, Basis, Confidence).
   - Architectural Discrepancy Warnings.
   - Recommended synchronization actions for mobile teams.
