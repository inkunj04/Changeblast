---
description: Inspect cross-platform feature parity and correspondences between Android and iOS
argument: none
---

# /changeblast:parity

Analyzes the codebase for shared cross-platform feature implementations across Android (Kotlin, Java) and iOS (Swift).

## Execution Steps

1. Run parity analysis in read-only mode:
   ```bash
   changeblast parity --format json
   ```
2. Parse JSON response:
   - List correlated features linking Android and iOS symbols.
   - Identify evidence basis (`api_contract`, `screen_flow`, `feature_mapping`).
   - Highlight architectural discrepancies and divergence notes.
3. Present parity report with mandatory divergence warning:
   - Never assume identical behavior across platforms.
