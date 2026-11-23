# ChangeBlast

**Deterministic Mobile Change-Impact Intelligence for Android and iOS**

ChangeBlast is an open-source change-impact intelligence tool purpose-built for native Android (Kotlin, Java) and native iOS (Swift) codebases. It performs deterministic static abstract syntax tree (AST) analysis and dependency graph traversal to calculate the blast radius of code modifications before committing or merging pull requests.

ChangeBlast operates under a strict **100% read-only invariant**: it never modifies application source code, never alters Git working trees or history, never runs repository build tools (such as Gradle or Xcodebuild), and requires zero external AI API keys or network access.

---

## The Problem and Solution

### The Problem
Modern mobile applications have complex architectural layers with lifecycle-dependent components:
- **Hidden transitive blast radius**: Changing a shared database entity, dependency injection binding, or API model often silently cascades into UI view models, background workers, deep links, or subscription billing flows.
- **Expensive verification cycles**: Running comprehensive end-to-end mobile device test matrices or full UI test suites for every minor commit is slow and cost-prohibitive.
- **Architectural divergence**: Monorepos containing both Android and iOS apps frequently evolve out of sync. While they may share backend API contracts, their platform lifecycles and runtime execution models differ fundamentally.

### The Solution
ChangeBlast provides fast, deterministic impact intelligence directly in developer workflows:
1. **Local AST Analysis**: Uses Tree-sitter parsers for Kotlin, Java, and Swift to extract symbols, inheritance, method declarations, invocations, and annotations without compiling code.
2. **In-Memory Dependency Graph**: Maps call graphs, inheritance hierarchies, and module boundaries into a directed graph with cycle detection and depth limiting.
3. **Mobile Domain Intelligence**: Applies rule-based heuristics across 10 core architectural domains per platform (lifecycle, reactive state, persistence, background execution, navigation, DI, networking, entitlements).
4. **Transparent Risk Classification**: Decouples impact severity from static confidence levels, showing developers exact evidence trails rather than opaque heuristic guesses.
5. **Claude Code Native**: Delivered as a native Claude Code plugin, enabling developers to query blast radius, review PR impact, and verify test coverage using natural language or slash commands.

---

## Key Capabilities

* **Deterministic Static AST Parsing**: Fast, offline syntax parsing of Kotlin (`.kt`, `.kts`), Java (`.java`), and Swift (`.swift`) using Tree-sitter adapters.
* **In-Memory Directed Dependency Graph**: Tracks symbol nodes, file nodes, module nodes, and test nodes with configurable traversal depth limits and stack-based cycle detection.
* **10 Android Architectural Domains**:
  1. Activity & Fragment Lifecycle
  2. Jetpack Compose State & Recomposition
  3. Navigation & Deep Links
  4. Runtime Permissions
  5. AndroidManifest Configuration
  6. WorkManager & Background Tasks
  7. Room & DataStore Persistence
  8. Dependency Injection (Hilt, Dagger)
  9. Networking (Retrofit, OkHttp)
  10. Google Play Billing Entitlements
* **10 iOS Architectural Domains**:
  1. UIViewController Lifecycle
  2. SwiftUI State & Observation
  3. NavigationStack & Coordinators
  4. App & Scene Lifecycle
  5. Background Tasks (`BGTaskScheduler`)
  6. Notifications & Universal Links
  7. Core Data & SwiftData Persistence
  8. Keychain Services
  9. Dependency Injection (Swinject, Needle)
  10. StoreKit 2 Entitlements
* **Cross-Platform Feature Parity with Divergence Warnings**: Correlates related Android and iOS features via API contracts and screen identifiers while enforcing explicit warnings that mobile implementations differ behaviorally.
* **Dual-Axis Risk Engine**:
  - **Severity**: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
  - **Confidence**: `VERIFIED`, `STRONG_INFERENCE`, `POSSIBLE`, `UNKNOWN`
* **Zero External Dependencies**: Operates completely offline with zero outbound network calls and zero LLM API requirements in the Python engine.

---

## Supported Platforms & Project Formats

ChangeBlast automatically detects and scans:

| Platform / Structure | Supported Formats |
| :--- | :--- |
| **Android** | Gradle multi-module projects (`settings.gradle`, `settings.gradle.kts`, `build.gradle`, `build.gradle.kts`), AndroidManifest.xml |
| **iOS** | Xcode Projects (`.xcodeproj`), Xcode Workspaces (`.xcworkspace`), Swift Package Manager (`Package.swift`) |
| **Languages** | Kotlin (`.kt`, `.kts`), Java (`.java`), Swift (`.swift`) |
| **Repositories** | Single-platform Android repositories, single-platform iOS repositories, and mixed Android/iOS monorepos |
| **Version Control** | Git 2.20+ (working tree uncommitted changes, staged changes, commit comparisons, and branch comparisons) |

---

## Installation for Claude Code

ChangeBlast is distributed as a plugin for **Claude Code**.

### 1. Install via Plugin Marketplace

Add the ChangeBlast marketplace catalog and install the plugin:

```text
/plugin marketplace add changeblast/changeblast
/plugin install changeblast@changeblast
```

Or install directly in one step if configured in your environment:

```text
/plugin install changeblast --marketplace changeblast/changeblast
```

### 2. Local Plugin Development Setup

To run ChangeBlast locally within Claude Code without installing from a remote marketplace:

```bash
claude --plugin-dir /path/to/changeblast
```

### 3. Engine Prerequisites

The ChangeBlast analysis engine requires **Python 3.11+** and **Git** available in your `PATH`:

```bash
# Clone the repository
git clone https://github.com/changeblast/changeblast.git
cd changeblast

# Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify your local installation:

```bash
changeblast --version
changeblast doctor
```

---

## Usage Examples

### Claude Code Slash Commands

When working in Claude Code, ChangeBlast provides dedicated slash commands:

* `/changeblast setup`: Inspect Python runtime, Tree-sitter parsers, Git availability, and repository topology.
* `/changeblast analyze [ref]`: Compute full blast radius for current changes or against a base git reference (e.g. `/changeblast analyze origin/main`).
* `/changeblast diff [ref]`: Display symbol-level modifications (classes, methods, line ranges) in changed files.
* `/changeblast commit`: Perform pre-commit validation to flag high-severity risks and untested components before committing.
* `/changeblast pr [base]`: Generate an impact summary table suitable for pull request descriptions.
* `/changeblast parity`: Correlate cross-platform features between Android and iOS modules.
* `/changeblast investigate <symbol>`: Trace caller hierarchies, upstream dependencies, and lifecycle risks for a specific symbol.

### Natural Language Queries in Claude Code

You can also prompt Claude Code directly:
* *"What is the blast radius of my staged Git changes?"*
* *"Which Android activities and Jetpack Compose screens are affected by changes to `UserSessionRepository`?"*
* *"Did my Swift StoreKit updates introduce any risks to subscription entitlements?"*

### CLI Commands

You can run ChangeBlast directly from your terminal:

```bash
# Analyze blast radius of uncommitted changes (Markdown output)
changeblast analyze --repo . --format markdown

# Analyze changes against a specific base branch (JSON output)
changeblast analyze --repo . --base-ref origin/main --format json

# Inspect symbol-level diffs
changeblast diff --repo . --format summary

# Check cross-platform feature parity across Android and iOS modules
changeblast parity --repo . --format json

# Diagnostic environment and parser check
changeblast doctor --repo .

# Export JSON schemas for data contracts
changeblast schema --model all
```

---

## Known Limitations

* **Pure Static Analysis**: ChangeBlast does not execute runtime bytecode or dynamic class loading. Symbols accessed exclusively via runtime reflection, string-based bundle lookups, or third-party binary libraries without source are not resolved.
* **Lexical and AST Scope**: In-memory dependency graph traversal correlates direct and transitive references across parsed source roots; unresolved external library symbols are marked with `POSSIBLE` or `UNKNOWN` confidence rather than assumed.
* **No Behavioral Parity Assumptions**: Cross-platform correlation identifies corresponding architectural components (e.g. shared endpoints or screen names), but ChangeBlast deliberately does not assume identical business logic or timing between Android and iOS.
* **Git Repository Requirement**: Change changeset extraction requires a valid Git repository with at least one commit.

---

## Development Instructions

### Local Environment Setup

ChangeBlast uses modern Python tooling (`uv` or `pip`, `ruff`, `mypy`, `pytest`):

```bash
# Clone the repository
git clone https://github.com/changeblast/changeblast.git
cd changeblast

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package in editable mode with development dependencies
pip install -e ".[dev]"
```

### Running Tests and Coverage

```bash
# Run complete test suite with coverage
pytest tests/ --cov=changeblast -v

# Run only unit tests
pytest tests/unit/ -v

# Run performance benchmarks
pytest tests/unit/test_performance_benchmarks.py -v
```

### Code Formatting, Linting, and Type Checking

ChangeBlast enforces strict type hints and zero lint warnings:

```bash
# Lint and format checking
ruff check .
ruff format --check .

# Strict static type checking
mypy src tests
```

### Claude Code Plugin Validation

Verify the Claude Code plugin manifest and directory profile using the Claude CLI:

```bash
claude plugin validate --strict .
claude plugin validate --profile directory .
```

---

## License

This project is licensed under the [MIT License](LICENSE).
