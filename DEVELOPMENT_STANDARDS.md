# ChangeBlast: Development Standards & Engineering Guidelines

This document defines the coding, testing, architecture, and version control standards enforced across the ChangeBlast project. Every contributor and automated agent must adhere to these conventions.

---

## 1. Code Style & Typing Standards

### 1.1 Python Language Baseline
- Target Python `>= 3.11`.
- Leverage modern Python syntax:
  - PEP 604 union types: `int | None` instead of `Optional[int]`.
  - Built-in generics (PEP 585): `list[str]`, `dict[str, Symbol]` instead of `typing.List`, `typing.Dict`.
  - Pattern matching (`match / case`) where appropriate for AST node classification.
  - Standard library `pathlib.Path` for all filesystem operations (no raw string manipulation with `os.path`).

### 1.2 Strict Type Checking with Mypy
- ChangeBlast enforces `mypy --strict`.
- Every function, method, and class attribute must carry explicit type annotations.
- `Any` is strictly forbidden in domain and use-case code. In external library adapter boundaries (such as raw Tree-sitter C pointers), isolate type casts behind well-typed helper functions.
- Configuration in `pyproject.toml`:
  ```toml
  [tool.mypy]
  python_version = "3.11"
  strict = true
  warn_return_any = true
  warn_unused_configs = true
  disallow_untyped_defs = true
  disallow_any_generics = true
  ```

### 1.3 Linting & Formatting with Ruff
- Line length: **100 characters**.
- Formatted and linted exclusively via `ruff`.
- Active rule sets:
  - `E`, `W` (pycodestyle errors and warnings)
  - `F` (Pyflakes)
  - `I` (isort import sorting)
  - `B` (flake8-bugbear)
  - `SIM` (flake8-simplify)
  - `UP` (pyupgrade)
  - `S` (flake8-bandit security checks)
  - `T20` (flake8-print - disallows unapproved `print()` calls in production engine code)

---

## 2. Architectural Governance

### 2.1 The Inward Dependency Invariant
Dependencies must strictly point inward toward the domain:
```
changeblast/
├── core/
│   ├── domain/       <-- Zero external dependencies (Pure Python + Pydantic contracts)
│   ├── ports/        <-- Abstract interfaces (abc.ABC)
│   └── use_cases/    <-- Orchestration logic (imports only from domain and ports)
└── adapters/         <-- Concrete implementations (Tree-sitter, Git CLI, NetworkX, Typer)
```
- **Rule 1**: `core/domain` must NEVER import from `adapters`, `tree_sitter`, `typer`, or `networkx`.
- **Rule 2**: `core/use_cases` must interact with external tools and infrastructure ONLY through abstract ports declared in `core/ports`.
- **Rule 3**: Tree-sitter `Node` and `Tree` objects must be translated to `Symbol` or `CallEdge` domain models immediately inside the parser adapter. No raw Tree-sitter objects may escape into use cases.

### 2.2 Error Handling & Resilience
- Never use bare `except:` or `except Exception:` without logging or re-raising.
- Define explicit domain exceptions deriving from `ChangeBlastError`:
  - `GitRepositoryNotFoundError`
  - `UnsupportedLanguageError`
  - `AstParsingError`
  - `SymbolResolutionError`
  - `SecurityBoundaryViolationError`

---

## 3. Testing Standards & Test Architecture

### 3.1 Test Organization
```
tests/
├── conftest.py           # Shared fixtures, temporary repository factories
├── unit/                 # Pure unit tests (isolated, in-memory, execution time < 1ms)
│   ├── domain/
│   ├── use_cases/
│   └── parsers/
├── integration/          # Multi-component integration tests (Git CLI, full pipeline)
│   ├── test_git_adapter.py
│   └── test_cli.py
└── fixtures/             # Real and synthetic source files for parsing validation
    ├── kotlin/
    ├── java/
    └── swift/
```

### 3.2 Testing Conventions (AAA Pattern)
Every test must clearly demonstrate **Arrange, Act, Assert**:

```python
def test_blast_radius_calculator_identifies_transitive_callers() -> None:
    # Arrange
    graph = create_in_memory_call_graph(
        [
            ("UserService.login", "AuthManager.authenticate"),
            ("AuthManager.authenticate", "TokenSigner.sign"),
        ]
    )
    calculator = BlastRadiusCalculator()
    modified = [SymbolRef("TokenSigner.sign")]

    # Act
    impact = calculator.compute_impact(modified, graph)

    # Assert
    assert "AuthManager.authenticate" in impact.direct_dependents
    assert "UserService.login" in impact.transitive_dependents
```

### 3.3 Test Naming Standard
All test functions must follow the descriptive pattern:
`test_<unit_or_feature>_<scenario_under_test>_<expected_outcome>()`

### 3.4 In-Memory Test Doubles (Ports & Adapters)
Unit tests for use cases must never spawn subprocesses, invoke `git`, or hit the disk. Inject test-double implementations of ports:
- `InMemoryGitDiffPort`
- `InMemorySymbolIndexer`
- `InMemoryAstParserPort`

### 3.5 Quality Gates
- **Code Coverage**: Minimum **90% line and branch coverage** enforced via `pytest-cov`.
- **Deterministic**: Tests must pass consistently regardless of execution order (`pytest-randomly` friendly).

---

## 4. Git Workflow & Version Control

ChangeBlast follows **Trunk-Based Development** with short-lived feature branches:

### 4.1 Branch Naming Convention
- `feat/<short-description>`: New capabilities or features.
- `fix/<short-description>`: Bug fixes and edge-case corrections.
- `refactor/<short-description>`: Code restructuring without behavior changes.
- `chore/<short-description>`: Tooling, dependencies, CI configuration.
- `docs/<short-description>`: Documentation changes.

### 4.2 Conventional Commits
Commit messages must strictly follow the Conventional Commits 1.0.0 format:

```text
<type>(<scope>): <short description in imperative mood>

[optional longer body explaining WHY the change was made]

[optional footer referencing issue/PR]
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`.

**Examples**:
- `feat(parser): add tree-sitter query extraction for swift extensions`
- `fix(git): resolve relative path calculation on windows drives`
- `test(graph): add cyclic dependency test cases for blast radius`

### 4.3 Atomic Commits
- Each commit represents a single logical change that compiles and passes all tests.
- Never mix automated formatting/refactoring with functional feature changes.
