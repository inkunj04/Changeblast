---
description: Deep dive into a specific symbol's call hierarchy, dependents, and failure modes
argument: <symbol-name>
---

# /changeblast:investigate

Traces the dependency graph and failure consequences of a specific symbol.

## Execution Steps

1. Execute filtered impact analysis for the target symbol:
   ```bash
   changeblast analyze --symbol $ARGUMENT --format json
   ```
2. Parse the JSON response:
   - Extract target symbol coordinates and mobile architectural domain.
   - Map callers and downstream dependents in the blast radius.
   - Extract concrete runtime failure modes.
   - Extract recommended unit/UI test suites.
3. Render investigation report following `templates/investigation_report.md`.
