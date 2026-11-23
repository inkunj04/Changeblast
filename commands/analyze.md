---
description: Compute change blast radius, affected UI screens, and recommended tests
argument: [git-ref]
---

# /changeblast:analyze

Calculates the deterministic change blast radius of uncommitted changes or a specific git reference across Android and iOS source code.

## Execution Steps

1. Execute the analysis command in read-only mode:
   ```bash
   changeblast analyze --format json $ARGUMENT
   ```
2. Parse the structured JSON output:
   - If `summary.total_files_changed == 0`: Report that the working tree is clean.
   - Extract `overall_risk.level`, `overall_risk.score`, and `overall_risk.confidence`.
   - Extract directly modified symbols and impacted UI entry points.
   - Extract mobile architectural domain findings (`LIFECYCLE`, `STATE_RECOMPOSITION`, `BILLING_SUBSCRIPTIONS`, etc.) and potential consequences.
   - Extract suggested regression test files and cross-platform correlations.
3. Present the structured report to the developer:
   - Separate Risk Severity from Confidence.
   - Provide the checklist of recommended tests.
   - Disclose static analysis limitations.
