# Workflow: Setup & Environment Verification (`/changeblast setup`)

This workflow checks whether the ChangeBlast Python analysis engine is installed, detects the current virtual environment, verifies Tree-sitter parsers, and guides the developer.

## Step-by-Step Execution

1. **Detect Engine Execution Path**:
   Execute the following non-modifying check in the workspace:
   ```bash
   which changeblast || test -f .venv/bin/changeblast && echo ".venv/bin/changeblast" || which python3
   ```

2. **Run Doctor Diagnostics**:
   If `changeblast` or a virtualenv binary is found:
   ```bash
   changeblast doctor --format json
   ```
   (Substitute with `.venv/bin/changeblast` or `python3 -m changeblast` as appropriate.)

3. **Interpret Doctor Output**:
   The JSON returns:
   - `status`: `"healthy"` or `"degraded"`
   - `python_version`: Must be `>= 3.11`
   - `git_version`: Verifies safe structured git execution
   - `tree_sitter_parsers`: Availability of Kotlin, Java, and Swift grammars
   - `repository`: Detected platforms (Android, iOS) and build systems
   - `issues`: Any non-fatal or blocking errors

4. **Present Diagnosis to Developer**:
   - If **healthy**: Confirm all systems are ready and suggest running `/changeblast analyze`.
   - If **missing or degraded**:
     - Explicitly detail what is missing (e.g. Tree-sitter grammars, Python version < 3.11).
     - **NEVER** run `pip install` automatically.
     - Provide the exact copy-paste command for the developer:
       ```bash
       pip install -e .
       # or with uv
       uv pip install -e .
       ```
