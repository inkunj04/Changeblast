---
description: Review pull request impact and generate a markdown PR summary table
argument: [base-branch]
---

# /changeblast:pr

Analyzes differences against a base branch (default `origin/main` or `main`) and generates a formatted PR impact table for PR descriptions.

## Execution Steps

1. Execute branch impact analysis:
   ```bash
   changeblast analyze --base ${ARGUMENT:-origin/main} --target HEAD --format json
   ```
2. Parse JSON response and format into the standard PR template:
   - PR risk badge, risk score, and confidence level.
   - Blast radius metrics and affected UI entry points.
   - Domain failure risks table.
   - Cross-platform feature parity table and divergence warnings.
   - Targeted regression test checklist.
3. Invariants:
   - Never approve or merge the PR automatically.
   - Never claim tests have been executed.
