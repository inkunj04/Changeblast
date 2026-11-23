# ChangeBlast

**Deterministic Mobile Change-Impact Intelligence for Android and iOS**

ChangeBlast is a production-quality, open-source change-impact intelligence tool purpose-built for native Android (Kotlin, Java) and native iOS (Swift) applications. It computes the blast radius of code changes before you commit or merge, mapping modified symbols directly to impacted UI entry points, downstream components, lifecycle hooks, and targeted regression test suites.

ChangeBlast operates under a strict **100% read-only invariant**: it never modifies application source code, never alters Git state, never runs arbitrary build scripts, and requires zero external AI API keys or network calls.

---

## Claude Code Plugin Installation

ChangeBlast is distributed as a first-class plugin for **Claude Code**.

### 1. Install from Marketplace

Install ChangeBlast directly into Claude Code in one step:

```text
/plugin install changeblast --marketplace changeblast/changeblast
```

Or add the repository marketplace first:

```text
/plugin marketplace add changeblast/changeblast
/plugin install changeblast@changeblast
```

### 2. Local Plugin Development

For local development or testing without publishing:

```bash
claude --plugin-dir /path/to/changeblast
```

---

## Python Engine Setup

ChangeBlast's AST analysis and graph traversal engine requires **Python 3.11+**:

```bash
# Clone the repository
git clone https://github.com/changeblast/changeblast.git
cd changeblast

# Install in editable mode
pip install -e .

# Or using uv
uv pip install -e .
```

Verify your installation:

```bash
changeblast --version
changeblast doctor
```

---

## Developer Commands

The ChangeBlast Claude Code plugin provides targeted slash commands:

| Command | Description |
| :--- | :--- |
| `/changeblast setup` | Verify Python environment, Tree-sitter parsers, and repository readiness. |
| `/changeblast analyze [ref]` | Compute the full blast radius, affected UI components, and recommended tests. |
| `/changeblast diff [ref]` | Inspect symbol-level changes (classes, methods, signatures, changed lines). |
| `/changeblast commit` | Pre-commit safety check: flags breaking changes and missing test coverage. |
| `/changeblast pr [base]` | Review pull request impact and generate a standardized PR summary table. |
| `/changeblast parity` | Inspect cross-platform feature correspondences between Android and iOS. |
| `/changeblast investigate <symbol>` | Deep-dive into a specific symbol's caller hierarchy and runtime risks. |

You can also interact with ChangeBlast in natural language, for example:
> *"What is the blast radius of my current changes?"*
> *"Which Android and iOS screens are affected by this API model update?"*

---

## Key Capabilities

* **Mobile Architecture Heuristics**: Analyzes 10 core architectural domains per platform:
  * **Android**: Activity/Fragment lifecycle, Jetpack Compose recomposition, Navigation deep links, Runtime permissions, Manifest entries, WorkManager background tasks, Room persistence, Hilt DI, Retrofit networking, and Google Play Billing.
  * **iOS**: UIViewController lifecycle, SwiftUI state observation, NavigationStack routing, App/Scene lifecycle, BGTaskScheduler, Core Data, Keychain services, Swinject DI, URLSession networking, and StoreKit 2 subscriptions.
* **Cross-Platform Divergence Warnings**: Correlates features sharing identical API contracts or navigation flows while explicitly warning developers of platform behavioral differences.
* **Deterministic & Offline**: Uses Tree-sitter AST parsing and in-memory digraph traversal. No telemetry, no external AI dependencies.
* **Separation of Severity and Confidence**: Never conflates high-risk blast radius with uncertain static analysis inference.

---

## License

Apache-2.0 © ChangeBlast Core Team
