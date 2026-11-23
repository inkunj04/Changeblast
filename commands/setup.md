---
description: Verify Python environment, Tree-sitter parsers, and repository readiness
argument: none
---

# /changeblast:setup

Verifies the ChangeBlast Python analysis engine, virtual environment, and Tree-sitter parsers without making any modifications.

## Execution Steps

1. Find the `changeblast` executable:
   ```bash
   which changeblast || test -f .venv/bin/changeblast && echo ".venv/bin/changeblast" || which python3
   ```
2. Execute the doctor command:
   ```bash
   changeblast doctor --format json
   ```
   *(Substitute with `.venv/bin/changeblast` or `python3 -m changeblast` if not in global PATH).*
3. Parse the JSON response:
   - Verify Python version >= 3.11.
   - Verify Git binary availability.
   - Verify Kotlin, Java, and Swift Tree-sitter parsers.
   - Detect repository platforms (Android, iOS).
4. Report status clearly:
   - If healthy, inform the user that ChangeBlast is ready.
   - If missing or degraded, provide copy-paste installation instructions (`pip install -e .`). Do NOT install packages automatically.
