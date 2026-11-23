# Workflow: Pre-Commit Safety Check (`/changeblast commit`)

Performs a pre-commit verification of staged or working tree changes to prevent regressions, runtime crashes, and untested modifications before finalizing a commit.

## Step-by-Step Execution

1. **Run Impact Analysis**:
   ```bash
   changeblast analyze --format json
   ```

2. **Evaluate Commit Safety Criteria**:
   Check the JSON report for:
   - **Critical / Breaking Changes**: Does `overall_risk.level == "critical"` or are there breaking change signals?
   - **Untested Changes**: Are there symbols listed under `missing_test_coverage`?
   - **High-Risk Mobile Domains**: Are there unverified modifications in `BILLING_SUBSCRIPTIONS`, `PERMISSIONS`, `MANIFEST_CONFIGURATION`, or `PERSISTENCE`?

3. **Present Pre-Commit Feedback**:
   - If **SAFE** (`LOW` risk, tests covered):
     > *"✅ Pre-commit safety check passed. Changes are well-contained and covered by recommended tests."*
   - If **WARNING** (`MEDIUM` or `HIGH` risk, or missing test coverage):
     > *"⚠️ Caution: Changes affect [X] components with missing test coverage. Recommend running [TestName] before committing."*
   - If **BLOCKING / CRITICAL** (`CRITICAL` severity, breaking public APIs, or unacknowledged billing transitions):
     > *"🚨 High Risk Commit Detected: [Reason]. Review the potential consequence: [Consequence]. Verify suggested regression tests before committing."*

4. **Strict Rules**:
   - **NEVER** run `git commit` or `git add` automatically.
   - **NEVER** modify source files.
   - Provide feedback and allow the developer to decide.
