---
name: changeblast
description: Deterministic mobile change-impact intelligence for native Android (Kotlin, Java) and iOS (Swift) codebases. Use when analyzing code changes, calculating blast radius, evaluating risk, detecting breaking changes, inspecting cross-platform parity, conducting PR reviews, or planning targeted regression tests before committing mobile code.
---

# ChangeBlast Mobile Change-Impact Intelligence

ChangeBlast computes the blast radius of mobile code changes before you commit or merge. It maps AST-level symbol changes to impacted UI entry points, downstream components, mobile architecture lifecycle hooks, and targeted regression test suites.

## Strict Read-Only & Safety Invariant

ChangeBlast is an intelligence tool, not an auto-refactoring or execution agent:
- **NEVER** modify source files or repository code.
- **NEVER** automatically install packages or run package managers without explicit user request.
- **NEVER** execute arbitrary repository build scripts (`./gradlew`, `xcodebuild`, `fastlane`).
- **NEVER** claim tests were executed when they were merely recommended.
- **NEVER** invent dependencies or hallucinate semantic relationships without static evidence.
- **NEVER** approve a pull request or code change automatically.

---

## Workflow Decision Tree

Identify the developer's intent and follow the corresponding workflow:

```text
User Request / Command
  ├── Environment check, installation diagnosis, or setup?
  │     └── Run /changeblast setup -> See [workflows/setup.md](file:///skills/changeblast/workflows/setup.md)
  │
  ├── Blast radius, impact assessment, or affected screens?
  │     └── Run /changeblast analyze -> See [workflows/analyze.md](file:///skills/changeblast/workflows/analyze.md)
  │
  ├── AST symbol-level diff, modified methods, or changed lines?
  │     └── Run /changeblast diff -> See [workflows/diff.md](file:///skills/changeblast/workflows/diff.md)
  │
  ├── Pre-commit check, breaking change alert, or commit safety?
  │     └── Run /changeblast commit -> See [workflows/commit.md](file:///skills/changeblast/workflows/commit.md)
  │
  ├── Pull request review, impact summary table, or PR notes?
  │     └── Run /changeblast pr -> See [workflows/pr.md](file:///skills/changeblast/workflows/pr.md)
  │
  ├── Android vs. iOS parity, shared APIs, or platform correspondence?
  │     └── Run /changeblast parity -> See [workflows/parity.md](file:///skills/changeblast/workflows/parity.md)
  │
  └── Deep symbol trace, caller chain, or specific failure mode?
        └── Run /changeblast investigate -> See [workflows/investigate.md](file:///skills/changeblast/workflows/investigate.md)
```

---

## Engine Discovery & Invocation

When invoking the local Python analysis engine, discover the executable using the following order of precedence:

1. `changeblast` (if available in system `$PATH`)
2. `.venv/bin/changeblast` (local workspace virtualenv)
3. `venv/bin/changeblast` (alternative local virtualenv)
4. `uv run changeblast` (if `uv` is installed)
5. `python3 -m changeblast`

If the engine is missing or cannot be executed, **STOP** and direct the user to run setup:
```bash
pip install -e .
```
*(Do not run pip or uv automatically.)*

Always invoke the CLI in read-only mode requesting structured JSON:
```bash
<engine-cmd> analyze --format json [--base <ref>] [--target <ref>] [--symbol <name>]
```

---

## Interpretation Rules: Severity vs. Confidence

ChangeBlast strictly separates **Risk Severity** from **Evidence Confidence**:

| Metric | Dimension | Meaning |
| :--- | :--- | :--- |
| **Severity** | Impact | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` — Potential blast radius if broken. |
| **Confidence** | Verification | `VERIFIED`, `STRONG_INFERENCE`, `POSSIBLE`, `UNKNOWN` — Verifiable static proof. |

* **Rule**: A finding can be `CRITICAL` in severity (e.g. In-App Billing or StoreKit purchase listener change) even if confidence is `POSSIBLE` (indirect dynamic call). Always report both metrics independently.
* Detailed heuristics: See [references/risk_and_confidence.md](file:///skills/changeblast/references/risk_and_confidence.md).

---

## Mobile Architecture Heuristics

ChangeBlast evaluates 10 mobile domains per platform:
* **Android**: Activity/Fragment lifecycle, Jetpack Compose recomposition, Navigation deep links, Runtime permissions, Manifest entries, WorkManager background tasks, Room persistence, Hilt DI, Retrofit APIs, Play Billing. (See [references/android_heuristics.md](file:///skills/changeblast/references/android_heuristics.md))
* **iOS**: UIViewController lifecycle, SwiftUI observation, NavigationStack routing, App/Scene lifecycle, BGTaskScheduler, Core Data, Keychain, Swinject DI, URLSession, StoreKit 2. (See [references/ios_heuristics.md](file:///skills/changeblast/references/ios_heuristics.md))
* **Cross-Platform**: Never assume identical behavior across platforms. Always disclose architectural divergences.

---

## Static Analysis Disclosures

Every analysis report must communicate analysis boundaries to avoid false confidence:
* Reflection and dynamic dispatch cannot be fully statically proven.
* Dynamic deep link routing parameters constructed at runtime may bypass AST matching.
* OS low-memory process termination depends on runtime hardware state.
* See [references/static_analysis_limits.md](file:///skills/changeblast/references/static_analysis_limits.md).
