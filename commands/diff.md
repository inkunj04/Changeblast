---
description: Inspect semantic AST symbol-level diff and modified line ranges
argument: [base-ref] [target-ref]
---

# /changeblast:diff

Inspects semantic AST-level changes rather than raw line diffs, highlighting modified classes, methods, and signature changes.

## Execution Steps

1. Execute diff in read-only mode:
   ```bash
   changeblast diff --format json $ARGUMENT
   ```
2. Parse the structured JSON output:
   - List changed files with addition/deletion counts.
   - Group modified symbols by file.
   - Highlight whether signatures were altered or symbols were deleted.
   - Flag any potential breaking changes for downstream consumers.
3. Present the symbol-level diff clearly with file coordinates.
