# ChangeBlast: Phased Implementation Plan

This document establishes the official engineering roadmap for ChangeBlast. In compliance with architectural constraints, **Phase 0** establishes the tooling, architecture, contracts, and environment. Implementation of the Python engine will strictly begin in **Phase 1** following explicit user approval.

---

## Roadmap Overview

```
+-----------------------------------------------------------------------------------+
| Phase 0: Engineering Environment & Tooling Setup (CURRENT)                        |
| - Skills installation, Claude Code plugin workflow, architectural baselines      |
+-----------------------------------------+-----------------------------------------+
                                          | [Gate: User Sign-Off]
                                          v
+-----------------------------------------------------------------------------------+
| Phase 1: Core Domain Models & Contracts (Zero-Dependency Domain Core)             |
| - Pure models: Symbol, FileDiff, CallEdge, ImpactNode, RiskAssessment             |
+-----------------------------------------+-----------------------------------------+
                                          v
+-----------------------------------------------------------------------------------+
| Phase 2: Multi-Language Tree-sitter AST Parsers                                   |
| - Kotlin, Java, and Swift Tree-sitter query adapters & test suites               |
+-----------------------------------------+-----------------------------------------+
                                          v
+-----------------------------------------------------------------------------------+
| Phase 3: Git Diff Engine & Symbol Diff Correlator                                 |
| - Read-only unified diff parser & line-range to AST symbol mapping               |
+-----------------------------------------+-----------------------------------------+
                                          v
+-----------------------------------------------------------------------------------+
| Phase 4: Dependency Graph & Blast Radius Engine                                   |
| - In-memory directed call-graph, reverse BFS traversal, test target mapping      |
+-----------------------------------------+-----------------------------------------+
                                          v
+-----------------------------------------------------------------------------------+
| Phase 5: Risk Scoring Engine & CLI Layer                                          |
| - Deterministic risk matrix, Typer CLI, JSON serializer, Rich terminal presenter |
+-----------------------------------------+-----------------------------------------+
                                          v
+-----------------------------------------------------------------------------------+
| Phase 6: Claude Code Plugin Integration                                           |
| - Plugin manifest, slash commands, agent skills, and Claude Code test harness     |
+-----------------------------------------+-----------------------------------------+
                                          v
+-----------------------------------------------------------------------------------+
| Phase 7: End-to-End Testing, Open-Source Packaging & Documentation                |
| - Real-world Android/iOS test fixtures, CI/CD workflows, public GitHub release    |
+-----------------------------------------------------------------------------------+
```

---

## Detailed Phase Breakdown

### Phase 0: Engineering Environment & Tooling Setup (Status: Complete)
- [x] Inspect existing skills and execution environment.
- [x] Verify Skills CLI compatibility with Antigravity and project target `.agents/skills`.
- [x] Select and install verified development skills (`modern-python`, `architecture-patterns`, `python-testing-patterns`, `security-and-hardening`, `git-workflow-and-versioning`, `improve-codebase-architecture`).
- [x] Create dedicated ChangeBlast skill-development workflow (`changeblast-dev`).
- [x] Research dependencies, stable versions, and platform compatibility.
- [x] Establish architecture blueprint (`ARCHITECTURE.md`), tech stack (`TECH_STACK.md`), security policy (`SECURITY_POLICY.md`), and development standards (`DEVELOPMENT_STANDARDS.md`).
- [x] Define component contracts, domain ports, and Pydantic data schemas.

---

### Phase 1: Core Domain Models & Contracts
*Goal: Establish the zero-dependency domain foundation with strict typing and serialization.*
- **Tasks**:
  1. Initialize `pyproject.toml` with `uv` (PEP 621 metadata, PEP 735 dependency groups).
  2. Implement pure domain value objects and entities:
     - `changeblast.core.domain.enums`: `Language`, `SymbolKind`, `Visibility`, `RiskLevel`.
     - `changeblast.core.domain.models`: `SourceLocation`, `Symbol`, `FileDiff`, `CallEdge`, `ImpactedNode`, `RiskAssessment`, `AnalysisReport`.
  3. Define abstract ports in `changeblast.core.ports`:
     - `IGitDiffPort`, `IAstParserPort`, `ISymbolIndexerPort`, `IImpactAnalyzerPort`, `IReportRendererPort`.
  4. Write comprehensive unit tests for domain invariants, validation rules, and immutability.
- **Acceptance Criteria**:
  - `pytest tests/unit/domain/` passes with 100% coverage.
  - `mypy --strict src/` reports zero errors.
  - Pydantic models generate valid JSON schemas without circular references.

---

### Phase 2: Multi-Language Tree-sitter AST Parsers
*Goal: Build resilient, compiler-free AST parsers for Kotlin, Java, and Swift.*
- **Tasks**:
  1. Implement `TreeSitterParserAdapter` in `changeblast.adapters.parsers`:
     - Initialize grammars (`tree-sitter-kotlin`, `tree-sitter-java`, `tree-sitter-swift`).
  2. Implement Tree-sitter query extraction for:
     - **Kotlin**: Class, object, interface, companion object, top-level function, method, property, Compose `@Composable` annotation.
     - **Java**: Class, interface, record, enum, method, constructor, field, annotations.
     - **Swift**: Class, struct, protocol, enum, extension, function, initializer, property wrapper (`@State`, `@Binding`, `@MainActor`).
  3. Implement call-site and inheritance reference extraction.
  4. Build synthetic multi-language fixture repository (`tests/fixtures/kotlin/`, `tests/fixtures/java/`, `tests/fixtures/swift/`).
- **Acceptance Criteria**:
  - Accurate extraction of symbol boundaries, visibility, and signatures across all 3 languages.
  - Zero crashes on syntax-invalid or partially typed code snippets.

---

### Phase 3: Git Diff Engine & Symbol Diff Correlator
*Goal: Extract changed lines from Git diffs and map them to AST symbols.*
- **Tasks**:
  1. Implement `GitCliAdapter` in `changeblast.adapters.git`:
     - Execute read-only `git diff` with unified line markers.
     - Handle uncommitted changes, staged changes, and branch comparisons (`git diff base...target`).
     - Detect file additions, modifications, renames, and deletions.
  2. Implement `SymbolDiffCorrelator`:
     - Intersect modified line ranges `[start_line, end_line]` with symbol AST spans.
     - Differentiate between interface changes (method signature, return type, visibility) and internal body changes.
  3. Implement in-memory symbol indexing (`InMemorySymbolIndexer`) for fast cross-file lookups.
- **Acceptance Criteria**:
  - Unit tests verify accurate symbol mapping across complex multi-hunk diffs.
  - Refusal to execute if git working directory is not clean or target ref is invalid.

---

### Phase 4: Dependency Graph & Blast Radius Engine
*Goal: Traverse call and inheritance graphs to compute blast radius and identify test targets.*
- **Tasks**:
  1. Implement `NetworkXGraphAdapter` in `changeblast.adapters.graph`:
     - Construct directed multigraph representing `CALLS`, `EXTENDS`, `IMPLEMENTS`, `INSTANTIATES`.
  2. Implement `BlastRadiusCalculator`:
     - Reverse breadth-first traversal from directly modified symbols.
     - Configurable max depth with cycle detection to prevent recursion loops.
     - Classify nodes: Direct Caller (Depth 1), Transitive Caller (Depth 2+).
  3. Mobile-Specific Heuristics:
     - Detect **UI Entry Points**: Android `Activity`, `Fragment`, `ComposeScreen`; iOS `UIViewController`, `SwiftUIView`.
     - Detect **Test Targets**: Methods matching `*Test`, `@Test`, `@RunWith`, `XCTestCase`.
- **Acceptance Criteria**:
  - Call graph accurately identifies downstream callers and upstream dependents.
  - Recommends the minimal sufficient set of test classes covering the change.

---

### Phase 5: Deterministic Risk Scoring & CLI Layer
*Goal: Implement the deterministic risk matrix and Typer CLI.*
- **Tasks**:
  1. Implement `RiskScoringService`:
     - Evaluate public API breaks, inheritance depth, UI exposure, and test coverage gap.
     - Generate transparent, human-readable rationale for assigned risk scores.
  2. Implement CLI commands using `typer`:
     - `changeblast analyze [--ref <ref>] [--format json|markdown|rich] [--max-depth <n>]`
     - `changeblast symbols <file>` (diagnostic symbol inspector)
  3. Implement formatters:
     - `JsonReportRenderer` (exact match to `AnalysisReportSchema`).
     - `RichReportRenderer` (tables, risk score badges, tree view of blast radius).
- **Acceptance Criteria**:
  - CLI prints formatted reports or pure JSON to stdout with zero logging clutter.
  - Exit codes: `0` for success, non-zero for invalid parameters or fatal errors.

---

### Phase 6: Claude Code Plugin Integration
*Goal: Package and distribute ChangeBlast as a seamless Claude Code plugin.*
- **Tasks**:
  1. Create `.claude-plugin/plugin.json` manifest following official specs.
  2. Implement slash commands:
     - `commands/blast.md`: Invokes `changeblast analyze --format json` on current branch.
     - `commands/diff.md`: Inspects symbol-level changes before committing.
  3. Implement agent skill:
     - `skills/mobile-change-impact/SKILL.md`: Guides Claude Code to reason through blast radius reports, suggest test suites, and review PRs.
  4. Test with `claude plugin validate` and `claude --plugin-dir`.
- **Acceptance Criteria**:
  - Claude Code loads plugin cleanly without warnings.
  - Claude correctly interprets JSON payload and explains mobile impact risks to developers.

---

### Phase 7: Verification, Real-World Fixtures & Open-Source Release
*Goal: Validate on real-world open-source repositories and prepare public release.*
- **Tasks**:
  1. Test against real Android apps (e.g., NowInAndroid or simplified architecture samples).
  2. Test against real iOS apps (e.g., Swift open-source sample projects).
  3. Setup GitHub Actions CI:
     - Multi-OS matrix (macOS, Linux, Windows).
     - Ruff format & lint checks.
     - Mypy strict type checks.
     - Pytest with `>= 90%` coverage requirement.
  4. Publish documentation: `README.md`, `CONTRIBUTING.md`, `LICENSE` (Apache-2.0).
- **Acceptance Criteria**:
  - CI pipeline green on all platforms.
  - Zero external AI dependencies in the engine.
  - Read-only execution guaranteed under all inputs.
