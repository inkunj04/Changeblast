# ChangeBlast: Technology Stack Specification

This document defines the formal technology stack, dependencies, version baselines, and architectural justifications for ChangeBlast. Every component is chosen to meet the strict constraints of:
- 100% deterministic, offline execution (no external AI APIs in the Python engine).
- Read-only execution safety.
- Cross-platform native mobile analysis (Android Kotlin/Java + iOS Swift).
- Production-grade reliability, performance, and maintainability.

---

## 1. Core Technology Stack Matrix

| Category | Component / Library | Minimum Version | Target Version | Compatibility | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Runtime** | Python | `>= 3.11` | `3.11.x - 3.13.x` | CPython on macOS, Linux, Windows | Primary execution runtime |
| **Package Management** | `uv` | `>= 0.5.0` | Latest stable | Rust-native, cross-platform | Dependency resolution, lockfiles, venv isolation |
| **Parser Core** | `tree-sitter` | `>= 0.24.0` | `0.26.1` | Python bindings (C-ABI) | Incremental, resilient AST parsing |
| **Grammar: Java** | `tree-sitter-java` | `>= 0.23.0` | `0.23.5` | PyPI binary wheels | Native Android Java parsing |
| **Grammar: Kotlin** | `tree-sitter-kotlin` | `>= 1.1.0` | `1.1.0` | PyPI binary wheels | Modern Android Kotlin parsing |
| **Grammar: Swift** | `tree-sitter-swift` | `>= 0.7.0` | `0.7.4` | PyPI binary wheels | Native iOS Swift parsing |
| **Data Modeling** | `pydantic` | `>= 2.10.0` | `2.14.4` | Python `>= 3.10` | Immutability, contract validation, JSON serialization |
| **Graph Analysis** | `networkx` | `>= 3.4.0` | `3.4.2` | Python `>= 3.10` | Directed call-graph algorithms, cycle detection, path tracing |
| **CLI Framework** | `typer` | `>= 0.15.0` | `0.29.2` | Python `>= 3.11` | Type-driven CLI command dispatch and parameter parsing |
| **Terminal Output** | `rich` | `>= 13.8.0` | `13.9.4` | Python `>= 3.8` | Formatted markdown, diff trees, risk score banners |
| **Test Framework** | `pytest` | `>= 8.3.0` | `9.2.0` | Python `>= 3.10` | Unit, integration, and contract test runner |
| **Test Coverage** | `pytest-cov` | `>= 6.0.0` | `7.1.0` | Python `>= 3.9` | Line and branch coverage reporting (threshold: ≥ 90%) |
| **Test Mocks** | `pytest-mock` | `>= 3.14.0` | `3.17.0` | Python `>= 3.10` | Isolated filesystem and git execution doubles |
| **Linter / Formatter** | `ruff` | `>= 0.8.0` | `0.17.6` | Rust-native binary | Ultra-fast AST linting and PEP 8 formatting |
| **Static Type Checker**| `mypy` | `>= 1.13.0` | `2.4.1` | Python `>= 3.10` | Strict type validation (`strict = true`) |
| **Plugin Distribution**| Claude Code Plugin | Manifest v1 | Specification 2025/2026 | Anthropic Claude Code CLI | Public distribution, slash commands, agent skills |

---

## 2. In-Depth Component Specifications

### 2.1 Python Runtime (`>= 3.11`)
- **Rationale**: Python 3.11 introduced substantial performance improvements (Specializing Adaptive Interpreter, up to 10-60% faster than 3.10), fine-grained error tracebacks, and standard library `tomllib`. Python 3.11+ is supported across all Tier-1 platforms.
- **Support Window**: We support Python 3.11, 3.12, and 3.13. Python 3.15 is supported as forward-compatible.

### 2.2 Tree-sitter AST Parsing Engine
- **Why Tree-sitter?**
  - Robustness: Handles syntax errors gracefully without halting (crucial for uncommitted, in-progress code changes).
  - Multi-language uniformity: Provides a consistent C-level node API (`Node.type`, `Node.children`, `Node.named_children`, `Node.start_point`, `Node.end_point`) across Java, Kotlin, and Swift.
  - Zero compiler dependency: Does not require JDK, Android SDK, or Xcode toolchains to parse code.
- **Language Grammars**:
  - `tree-sitter-java (0.23.5)`: Fully parses modern Java constructs (records, sealed classes, pattern matching, annotations).
  - `tree-sitter-kotlin (1.1.0)`: Full support for Kotlin syntax (coroutines, extension functions, data classes, Jetpack Compose annotations).
  - `tree-sitter-swift (0.7.4)`: Covers modern Swift (macros, async/await, actors, property wrappers, SwiftUI syntax).

### 2.3 Graph Engine (`networkx` vs. Custom Graph)
- **Selection**: `networkx >= 3.4.0` encapsulated behind a Domain Port (`DependencyGraphPort`).
- **Rationale**: Provides verified, O(V + E) implementations for:
  - Directed Acyclic Graph (DAG) validation and cycle detection (`simple_cycles`).
  - Ancestor/Descendant traversal (`descendants`, `ancestors`) for blast radius discovery.
  - Shortest path / reachability tracing between modified code and test targets.
- **Decoupling**: The domain core never exposes NetworkX objects directly; all nodes and edges are mapped to pure domain value objects (`Symbol`, `CallEdge`).

### 2.4 Data Modeling (`pydantic 2.14+`)
- **Rationale**: Rust-backed core (`pydantic-core`) ensures microsecond serialization.
- **Features Used**:
  - `model_config = ConfigDict(frozen=True)` for immutable domain contracts.
  - Automatic JSON Schema generation to power Claude Code tool definitions and user configurations.

### 2.5 CLI Layer (`typer` + `rich`)
- **Selection**: `typer 0.29.2` with `rich 13.9.4`.
- **Rationale**:
  - Clean separation between CLI presentation and domain use cases.
  - Native support for both human-friendly interactive terminal output (`--format rich`) and machine-readable JSON piping (`--format json`).

### 2.6 Claude Code Plugin
- **Structure**:
  - Manifest: `.claude-plugin/plugin.json`
  - Slash Commands: `commands/blast.md`, `commands/diff.md`
  - Agent Skills: `skills/mobile-change-impact/SKILL.md`
- **Execution Mechanism**: The plugin issues read-only subcommands to `changeblast` CLI and formats the output for Claude's conversational review.

---

## 3. Evaluated & Rejected Alternatives

| Tool / Technology | Status | Reason for Rejection |
| :--- | :--- | :--- |
| **External LLM APIs (OpenAI / Anthropic API keys inside engine)** | **REJECTED** | Violates core constraint: engine must be 100% deterministic, offline, zero-cost, and zero-token. AI belongs exclusively in the Claude Code plugin client layer. |
| **Android SDK / `javaparser` / `kotlin-compiler-embeddable`** | **REJECTED** | Requires JVM runtime, Android SDK installation, heavy memory footprints (GBs), and fails on dirty/uncompilable git working trees. |
| **SourceKit / `SwiftSyntax` binary execution** | **REJECTED** | Requires macOS + Xcode installation. Would prevent running ChangeBlast on Linux CI/CD or Windows developer machines. Tree-sitter is 100% cross-platform. |
| **SQLite / PostgreSQL / Embedded Databases** | **REJECTED** | Violates read-only zero-state constraint. ChangeBlast operates ephemerally in-memory against the active git working tree or commit range. |
| **Poetry / Pipenv** | **REJECTED** | `uv` provides 10-100x faster dependency resolution, standardized PEP 735 dependency groups, and seamless cross-platform lockfile generation. |
| **Black + Flake8 + isort** | **REJECTED** | Superseded by `ruff`, which replaces all three with a single binary that is 50-100x faster and configured via standard `pyproject.toml`. |
