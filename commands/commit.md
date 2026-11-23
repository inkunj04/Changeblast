---
description: Run pre-commit safety check to detect breaking changes and untested code
argument: none
---

# /changeblast:commit

Evaluates staged and working tree changes to prevent regressions before committing.

## Execution Steps

1. Run impact analysis against the current working tree:
   ```bash
   changeblast analyze --format json
   ```
2. Verify safety criteria:
   - Check if `overall_risk.level == "critical"` or breaking changes are flagged.
   - Check if any modified symbol is in `missing_test_coverage`.
   - Check if sensitive mobile domains (`BILLING_SUBSCRIPTIONS`, `PERMISSIONS`, `MANIFEST_CONFIGURATION`) were touched.
3. Report verdict:
   - Pass: Inform user the changes are safe to commit.
   - Warning / Failure: Highlight untested components and potential consequences.
4. Invariants:
   - Never run `git commit` or `git add` automatically.
   - Never modify code.
