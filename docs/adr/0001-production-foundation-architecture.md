# ADR 0001: Phase 1 Production Foundation & Core Contracts

## Status
**Accepted** (2026-11-23)

## Context
ChangeBlast is a mobile change-impact intelligence tool for native Android (Kotlin/Java) and iOS (Swift) codebases. It is designed to be distributed as a Claude Code plugin with a local, deterministic Python engine.

In Phase 1, we must establish the foundational package structure, typed data models, JSON schema versioning, platform adapter interfaces (ports), CLI entry point, error handling, structured logging, and unit test suites before any parsing or dependency analysis is implemented.

## Decisions

### 1. Python Baseline & Modular Packaging
- Enforce Python `>= 3.11` using `pyproject.toml` (PEP 621) with `hatchling` as the build backend.
- Enforce modern typing idioms: PEP 604 union types (`X | Y`), PEP 585 generics (`list[str]`), and `enum.StrEnum`.

### 2. Immutable Data Contracts with Schema Versioning
- Implement data models using Pydantic v2:
  - `RepositoryProfile`: Workspace structure, mobile platform markers, detected build systems, and VCS metadata.
  - `ChangeSet`: File modifications, line ranges, and unified diff hunks.
  - `SourceSymbol`: Declaration entities with language, visibility, source location, container hierarchy, and entry point flags.
  - `DependencyEdge`: Directed invocation, inheritance, or reference edges between symbols.
  - `EvidenceReference`: Verifiable coordinates and snippets explaining findings.
  - `ImpactFinding`: Specific symbol impact findings with depth, propagation trail, UI impact, and test recommendations.
  - `ImpactReport`: Top-level report aggregating summary metrics, deterministic risk assessment, findings, and warnings.
  - `AnalysisWarning`: Non-fatal diagnostic conditions.
- Enforce `frozen = True` and `extra = "forbid"` across all models.
- Introduce `CURRENT_SCHEMA_VERSION = "1.0.0"` with major-version compatibility verification (`is_compatible_version()`) and JSON schema generation (`get_schema_for_model()`).

### 3. Hexagonal Architecture (Ports & Adapters)
- Decouple all external systems behind abstract ports in `changeblast.ports`:
  - `IVcsAdapter`: Abstraction for Git operations.
  - `ILanguageParserAdapter`: Abstraction for multi-language AST parsers (Kotlin, Java, Swift).
  - `IDependencyGraphAdapter`: Abstraction for directed call and dependency graph traversal.
  - `IReportFormatterAdapter`: Abstraction for JSON, Markdown, and terminal report rendering.
- Domain models and use cases have zero dependencies on external parser or CLI libraries.

### 4. Zero-Dependency CLI Entry Point with `argparse`
- Use Python's standard library `argparse` module for the CLI entry point (`changeblast`).
- Expose `analyze`, `schema`, and `profile` subcommands.
- Standardized exit codes:
  - `0`: Success.
  - `1`: Application / execution error.
  - `2`: CLI argument error.
  - `3`: Security boundary violation.

### 5. Defensive Security & Read-Only Execution
- Prevent path traversal by strictly verifying that all file paths resolve below the workspace root.
- All subprocess execution avoids `shell=True` and passes explicit argument vectors.
- The engine operates purely in-memory and read-only; no user files are modified.

### 6. Quality & Verification Gates
- Code linted and formatted with `ruff` (`line-length = 100`, rule sets: `E`, `W`, `F`, `I`, `B`, `SIM`, `UP`, `S`, `T20`).
- Strict type checking with `mypy` (`strict = true`).
- Comprehensive unit tests with `pytest` and `pytest-cov`, achieving $\ge 90\%$ test coverage.

## Consequences
- **Positive**: Clean separation of concerns allows Phase 2 (Tree-sitter AST parsers) and Phase 3 (Git diff integration) to be implemented without modifying existing domain contracts.
- **Positive**: Automated schema exports allow the Claude Code plugin to validate and consume ChangeBlast reports reliably.
- **Positive**: Zero external AI dependencies in the Python engine ensures 100% offline, deterministic, zero-token cost analysis.
