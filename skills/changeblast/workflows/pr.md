# Workflow: Pull Request Review (`/changeblast pr`)

Reviews changes between a feature branch and the target integration branch (defaulting to `origin/main` or `main`), producing a structured PR Impact Summary table ready for copy-pasting into GitHub/GitLab PR descriptions.

## Step-by-Step Execution

1. **Determine Base Branch**:
   - Default: `origin/main` (fallback: `main`, `master`, or `develop`).
   - If user provided argument (e.g. `/changeblast pr staging`): use specified base branch.

2. **Run PR Impact Analysis**:
   ```bash
   changeblast analyze --base <base-branch> --target HEAD --format json
   ```

3. **Render PR Impact Summary**:
   Format the output using the standard PR template in [templates/pr_impact_summary.md](file:///skills/changeblast/templates/pr_impact_summary.md):
   - **PR Risk Badge & Score**: `CRITICAL` / `HIGH` / `MEDIUM` / `LOW`
   - **Executive Summary**: Changed files, directly modified symbols, total blast radius.
   - **Impacted UI Entry Points**: Specific Activities, Fragments, SwiftUI Views, or ViewControllers affected.
   - **Architecture & Domain Risks**: Highlight database migrations, network protocol updates, or background workers modified.
   - **Targeted Regression Checklist**: Checkbox list of unit and UI tests recommended for verification.
   - **Analysis Disclosures**: Limitations of static evaluation.

4. **Safety Rule**:
   - **NEVER** automatically approve, merge, or create a PR.
