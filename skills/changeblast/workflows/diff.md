# Workflow: Symbol-Level Diff (`/changeblast diff`)

Inspects semantic AST-level changes rather than raw line diffs, highlighting modified declarations, added functions, removed classes, and signature changes.

## Step-by-Step Execution

1. **Parse Arguments**:
   - Optional `--base <ref>` or positional git refs.
   - Defaults to uncommitted changes relative to `HEAD`.

2. **Execute Engine**:
   ```bash
   changeblast diff --format json [--base <ref>] [--target <ref>]
   ```

3. **Format Diff Inspection**:
   - **Changed Files Summary**: Net additions and deletions.
   - **Semantic Symbol Changes**:
     - Class, Struct, Protocol, Interface modifications.
     - Method, Function, Property modifications.
     - Changed line ranges and whether the signature itself was altered.
   - **Breaking Change Alerts**:
     - Flag any **DELETED** public symbols or modified method parameter signatures that could break downstream callers.
