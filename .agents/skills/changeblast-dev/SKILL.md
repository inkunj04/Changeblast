---
name: changeblast-dev
description: Development workflow and guidelines for building, validating, and testing ChangeBlast Claude Code plugins and agent skills. Use when authoring or updating Claude Code plugin manifests, commands, skills, or connecting them to the ChangeBlast Python analysis engine.
---

# ChangeBlast Skill & Plugin Development Workflow

This skill guides the design, implementation, packaging, and testing of Claude Code plugins and skills for the **ChangeBlast** mobile change-impact intelligence system.

## 1. Claude Code Plugin Architecture Overview

ChangeBlast distributes its AI integration as a first-class **Claude Code plugin**. The plugin wraps the local, deterministic Python analysis engine (`changeblast` CLI) and exposes it to Claude Code as slash commands, agent skills, and contextual hooks.

### Standard Plugin Layout

ChangeBlast's Claude Code plugin follows the official specification:

```text
plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest (metadata, author, version)
├── commands/                # Custom user-facing slash commands
│   ├── blast.md             # /changeblast:blast - Run impact analysis on current branch
│   └── diff.md              # /changeblast:diff - Inspect symbol-level changes
├── skills/                  # Autonomous agent skills
│   └── mobile-change-impact/
│       ├── SKILL.md         # Contextual skill instructions for Claude
│       └── references/      # Domain knowledge (Kotlin/Swift impact heuristics)
│           ├── android.md
│           └── ios.md
├── hooks/
│   └── hooks.json           # Optional lifecycle hooks (e.g., pre-commit checks)
└── README.md                # User installation and configuration documentation
```

> **Crucial Path Convention**: All internal script paths in `hooks/hooks.json` or command execution must use `${CLAUDE_PLUGIN_ROOT}` rather than relative paths, ensuring execution works seamlessly when Claude Code caches the plugin globally.

---

## 2. Plugin Manifest (`.claude-plugin/plugin.json`)

The manifest specifies metadata and execution rules:

```json
{
  "name": "changeblast",
  "version": "0.1.0",
  "description": "Deterministic mobile change-impact intelligence for Android (Kotlin/Java) and iOS (Swift)",
  "author": {
    "name": "inkunj04",
    "url": "https://github.com/inkunj04/Changeblast"
  },
  "homepage": "https://github.com/inkunj04/Changeblast",
  "repository": "https://github.com/inkunj04/Changeblast.git",
  "license": "Apache-2.0",
  "keywords": [
    "mobile",
    "android",
    "ios",
    "kotlin",
    "swift",
    "static-analysis",
    "blast-radius",
    "change-impact"
  ]
}
```

---

## 3. Developing Commands (`commands/`)

Commands are markdown files placed flat in `commands/`. When the plugin is loaded, Claude Code registers them with the prefix `/<plugin-name>:<command-name>`.

### Example: `commands/blast.md`

```markdown
---
description: Run change-impact analysis against uncommitted changes or a target branch
argument: [git-ref]
---

# /changeblast:blast

Executes the ChangeBlast deterministic Python engine to calculate the blast radius of mobile code changes.

## Execution Steps:
1. Verify that `changeblast` is available in PATH or run via `uv run changeblast`.
2. Execute read-only analysis:
   ```bash
   changeblast analyze --format json --ref $ARGUMENT
   ```
3. Parse the structured JSON output.
4. Report:
   - Modified symbols (Classes, Methods, Interfaces)
   - Direct and transitive dependents
   - Impacted UI entry points (Activities, Fragments, ViewControllers, SwiftUI Views)
   - Recommended targeted unit and UI test suites
   - Risk score (Low / Medium / High / Critical)
```

---

## 4. Developing Agent Skills (`skills/`)

Skills teach Claude how to interpret mobile ASTs and reason about change impact autonomously when working in Android and iOS repositories.

Each skill lives in its own subdirectory under `skills/` and contains a `SKILL.md`:
- `name`: Matches skill directory name in `kebab-case`.
- `description`: Precise trigger conditions so Claude invokes the skill at the right moment.
- `SKILL.md` body: Step-by-step reasoning, mobile architecture heuristics (e.g., Android lifecycle, iOS delegate patterns, SwiftUI state propagation), and interpretation guidelines.

---

## 5. Integrating with the Python Engine

ChangeBlast enforces a strict architectural boundary between the **AI Plugin** and the **Python Engine**:
1. **Zero AI in the Python Engine**: The Python engine performs 100% deterministic, offline AST parsing and call-graph traversal using Tree-sitter. It outputs structured JSON.
2. **AI Layer in Claude Code**: The Claude Code plugin consumes the deterministic JSON output and leverages Claude's contextual reasoning to explain impacts, summarize risks, and guide PR reviews.
3. **Read-Only Invariant**: The engine never modifies workspace files or executes build tools (no `gradle`, no `xcodebuild`). It parses source files and runs `git diff` exclusively in read-only mode.

---

## 6. Local Testing and Validation

### Validating the Plugin Manifest
Run official validation via Claude Code CLI:
```bash
claude plugin validate ./plugin
```

### Testing Iteratively in Claude Code
Test the plugin locally during development without publishing:
```bash
claude --plugin-dir ./plugin
```

To reload plugins after updating skills or commands within an active Claude Code session:
```text
/reload-plugins
```

### Verification Checklist before Publishing
- [ ] Validated with `claude plugin validate`.
- [ ] No hardcoded absolute or local relative paths in hooks/scripts; uses `${CLAUDE_PLUGIN_ROOT}`.
- [ ] Read-only execution verified (engine has no file-write code paths).
- [ ] Python engine packaged with clean CLI entry points (`pyproject.toml` `[project.scripts]`).
- [ ] Clear error reporting when target repo is clean or not a git repository.
