# ADR 0005: Claude Code Plugin Architecture and Distribution

## Status
Accepted

## Context
ChangeBlast's primary user-facing distribution target is **Claude Code** (Anthropic's terminal-based agent). While development occurs within an Antigravity workspace, the delivered open-source product must be seamlessly installable, discoverable, and executable as a native Claude Code plugin from a public GitHub repository.

The product architecture enforces an absolute boundary between:
1. **The Deterministic Python Engine**: 100% offline, read-only AST parsing (Tree-sitter) and dependency graph traversal without external AI API dependencies.
2. **The Claude Code AI Layer**: Reasoning, explanation, interactive commands, and developer guidance powered by Claude Code via skills, workflows, and slash commands.

## Decision

### 1. Plugin Manifest Architecture
- Created `.claude-plugin/plugin.json` adhering to the official Anthropic plugin specification (kebab-case name `changeblast`, version `0.1.0`, description, author, license, and keywords).
- Created `.claude-plugin/marketplace.json` enabling one-step marketplace discovery and installation (`/plugin install changeblast --marketplace inkunj04/Changeblast`).
- Bundled compliant 512x512 PNG listing icon at `.claude-plugin/icon.png`.

### 2. Skill Architecture & Progressive Disclosure
- Created `skills/changeblast/SKILL.md` with standard YAML frontmatter and precise trigger conditions.
- Organized detailed domain knowledge into modular progressive disclosure subdirectories:
  - `skills/changeblast/workflows/`:
    - `setup.md`: Python engine verification and non-invasive setup diagnostics.
    - `analyze.md`: Blast radius calculation and UI impact reporting.
    - `diff.md`: Semantic AST symbol diff and signature modification inspection.
    - `commit.md`: Pre-commit safety check preventing breaking changes and regressions.
    - `pr.md`: PR impact review producing standardized GitHub/GitLab markdown tables.
    - `parity.md`: Cross-platform Android vs. iOS parity and divergence analysis.
    - `investigate.md`: Deep symbol trace through the call hierarchy.
  - `skills/changeblast/references/`:
    - `android_heuristics.md`: 10 Android architectural domains and failure consequences.
    - `ios_heuristics.md`: 10 iOS architectural domains and failure consequences.
    - `risk_and_confidence.md`: Absolute separation between impact severity and evidence confidence.
    - `json_schema.md`: Structural JSON schema interpretation.
    - `static_analysis_limits.md`: Transparent disclosures of static analysis boundaries.
  - `skills/changeblast/templates/`:
    - `pr_impact_summary.md`, `risk_disclosure.md`, `investigation_report.md`.

### 3. Developer Slash Commands (`commands/`)
- Created `commands/changeblast.md` dispatcher supporting `/changeblast <subcommand>`.
- Created individual command files:
  - `setup.md` (`/changeblast:setup`)
  - `analyze.md` (`/changeblast:analyze`)
  - `diff.md` (`/changeblast:diff`)
  - `commit.md` (`/changeblast:commit`)
  - `pr.md` (`/changeblast:pr`)
  - `parity.md` (`/changeblast:parity`)
  - `investigate.md` (`/changeblast:investigate`)

### 4. Safety & Invariants
- **Strict Read-Only**: The plugin and engine never modify source code, alter Git state, or run package managers without explicit user request.
- **No Arbitrary Scripts**: Never executes build tools (`gradle`, `xcodebuild`).
- **No Hallucinated Testing**: Never claims tests were executed when they were only recommended.
- **Separation of Severity and Confidence**: Never conflates high-risk impact with uncertain evidence.

## Consequences

### Positive
- Validated with `claude plugin validate --strict` and `claude plugin validate --profile directory` with zero warnings or errors.
- Genuinely installable from public GitHub via `/plugin install changeblast --marketplace <owner>/<repo>`.
- Fully documented workflows and templates for mobile engineering teams.

### Negative
- Developers must have a local Python 3.11+ environment with `changeblast` installed for the plugin commands to execute AST parsing.
