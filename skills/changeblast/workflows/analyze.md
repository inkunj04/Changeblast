# Workflow: Change-Impact Analysis (`/changeblast analyze`)

Computes the full blast radius, affected UI screens, mobile engineering failure risks, and targeted regression tests.

## Step-by-Step Execution

1. **Parse Developer Arguments**:
   - No argument: Analyze uncommitted working tree changes against `HEAD`.
   - Single git reference (e.g. `main`): Analyze changes between `main` and working tree (`--base main`).
   - Two git references (e.g. `origin/main feature/checkout`): Analyze changes between the two branches (`--base origin/main --target feature/checkout`).

2. **Execute Engine**:
   ```bash
   changeblast analyze --format json [--base <ref>] [--target <ref>]
   ```

3. **Handle Edge Cases**:
   - **No Changes Detected**: Inform the user cleanly:
     > *"Working tree is clean. No code changes detected relative to HEAD. To analyze a specific branch, pass a git reference: `/changeblast analyze origin/main`."*
   - **Not a Git Repository**: Inform the developer that ChangeBlast requires a valid Git repository to calculate changesets.

4. **Format Analysis Report**:
   Present the results using the standard sections:
   - **Executive Risk Assessment**:
     - Overall Risk Level (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and Score (0-100).
     - Overall Confidence Level (`VERIFIED`, `STRONG_INFERENCE`, `POSSIBLE`, `UNKNOWN`).
     - Key Risk Factors and Breaking Change Signals.
   - **Blast Radius Metrics**:
     - Total Files Changed, Directly Modified Symbols, Transitive Blast Components.
     - Affected UI Components (Activities, Fragments, ViewControllers, SwiftUI Views).
   - **Mobile Engineering Intelligence**:
     - Platform (`ANDROID` / `IOS`).
     - Architectural Domain (e.g. `BILLING_SUBSCRIPTIONS`, `STATE_RECOMPOSITION`).
     - Concrete potential consequence (e.g. unacknowledged auto-refund, recomposition loop).
   - **Recommended Regression Tests**:
     - Checkbox list of targeted test files to execute before merging.
   - **Static Analysis Limitations**:
     - Disclose reflection, dynamic deep link concatenation, or background process death boundaries.
