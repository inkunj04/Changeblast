---
description: ChangeBlast mobile change-impact intelligence dispatcher. Usage: /changeblast [setup|analyze|diff|commit|pr|parity|investigate]
argument: [subcommand] [args...]
---

# /changeblast

ChangeBlast dispatcher for mobile change-impact intelligence across Android (Kotlin, Java) and iOS (Swift).

## Execution Instructions

1. **Parse Subcommand**:
   Inspect the argument provided by the developer:
   - `setup` -> Execute the setup and environment diagnostics workflow.
   - `analyze` (or with git refs) -> Execute change-impact blast radius analysis.
   - `diff` (or with git refs) -> Inspect AST symbol-level diff.
   - `commit` -> Execute pre-commit safety check on working tree / staged changes.
   - `pr` (or with base branch) -> Generate pull request impact summary table.
   - `parity` -> Inspect cross-platform Android vs. iOS feature correspondences.
   - `investigate <symbol>` -> Trace deep caller path and failure modes for a symbol.
   - If no argument or unknown argument is provided, display usage guide:
     ```text
     Available ChangeBlast commands:
       /changeblast setup                 - Check Python engine and Tree-sitter health
       /changeblast analyze [ref]         - Calculate change blast radius and affected screens
       /changeblast diff [ref]            - Inspect symbol-level AST changes and modified methods
       /changeblast commit                - Run pre-commit safety check before committing
       /changeblast pr [base-branch]      - Generate PR impact summary table for PR descriptions
       /changeblast parity                - Inspect Android and iOS cross-platform feature parity
       /changeblast investigate <symbol>  - Deep dive into a symbol's caller path and risks
     ```

2. **Strict Invariants**:
   - 100% read-only operations. Never modify source code or run package managers.
   - Refer to `skills/changeblast/SKILL.md` for heuristics and interpretation rules.
