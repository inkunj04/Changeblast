# Contributing to ChangeBlast

Thank you for your interest in contributing to ChangeBlast. As an open-source tool built for mobile developers and engineering teams, we maintain high standards of code quality, deterministic behavior, and security.

---

## 1. Development Setup

### Prerequisites
- Python 3.11+
- Git 2.20+
- Node.js 18+ (for Claude Code plugin testing)

### Installation
```bash
# Clone the repository
git clone https://github.com/changeblast/changeblast.git
cd changeblast

# Create a dedicated virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install ChangeBlast in editable mode with test and development dependencies
pip install -e ".[dev]"
```

Verify your environment:
```bash
changeblast --version
changeblast doctor
```

---

## 2. Repository Layout

```
.
├── .claude-plugin/           # Claude Code plugin manifest & marketplace definitions
├── commands/                 # Claude Code slash command definitions
├── skills/                   # ChangeBlast agent skills, workflows, and references
├── src/changeblast/
│   ├── models/               # Typed domain contracts and versioned schemas (Pydantic v2)
│   ├── ports/                # Abstract adapter interfaces (VCS, Parser, Graph, Reporter)
│   ├── adapters/
│   │   ├── git/              # Safe read-only Git operations and path validation
│   │   ├── parsers/          # Tree-sitter AST adapters (Kotlin, Java, Swift)
│   │   ├── graph/            # In-memory directed dependency graph implementation
│   │   └── reporters/        # Formatters for Markdown, JSON, and summary tables
│   ├── discovery/            # Repository scanner for Gradle, Xcode, and monorepos
│   ├── analysis/             # Impact calculation, risk engine, and mobile domain heuristics
│   └── cli.py                # Command-line entry point
├── tests/
│   ├── unit/                 # Unit tests, security QA, and performance benchmarks
│   └── fixtures/             # Synthetic test repositories and sample AST fixtures
```

---

## 3. Code Standards & Quality Gates

Every code change must satisfy the following automated quality gates:

### Typing (`mypy`)
- Must pass `mypy --strict src tests` with zero errors.
- All function signatures, parameters, and return types must be explicitly typed.
- `Any` types are forbidden in domain logic.

### Linting & Formatting (`ruff`)
- Must pass `ruff check .` and `ruff format --check .`.
- Line length limit: 100 characters.

### Architecture Invariants
- **Strictly Read-Only**: The engine must never modify repository source files, create temporary files in user repos, or alter Git state.
- **Zero External Network Dependencies**: The Python engine must remain 100% offline. Do not add dependencies that make external HTTP calls or require third-party AI keys.
- **Path Traversal Protection**: All file paths derived from user input or Git output must be verified with `validate_path_within_root()`.

---

## 4. Testing Requirements

- All new features and bug fixes require automated tests in `tests/unit/`.
- Minimum statement coverage threshold: 85% (current coverage: >90%).
- Run tests locally:
  ```bash
  pytest tests/ --cov=changeblast -v
  ```
- Run performance and security benchmarks when modifying graph algorithms or path resolution:
  ```bash
  pytest tests/unit/test_performance_benchmarks.py tests/unit/test_security_qa.py -v
  ```

---

## 5. Claude Code Plugin Validation

When modifying plugin manifests, skills, or slash commands, run Claude plugin validation:
```bash
claude plugin validate --strict .
claude plugin validate --profile directory .
```

---

## 6. Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/my-enhancement
   ```
2. Commit changes using atomic, descriptive commit messages adhering to Conventional Commits:
   - `feat(...)`: New capability or domain heuristic.
   - `fix(...)`: Bug fix or security hardening.
   - `test(...)`: Additional tests or fixture coverage.
   - `docs(...)`: Documentation updates.
3. Verify all checks pass before pushing:
   ```bash
   ruff check . && ruff format --check . && mypy src tests && pytest tests/
   ```
4. Submit a Pull Request targeting `main`. Provide a clear summary of changes and reference relevant issues.

---

## 7. Reporting Bugs

- Search existing issues to verify the problem has not already been reported.
- Open a GitHub Issue detailing:
  - Expected vs. actual behavior.
  - Project configuration (Android Gradle, Xcode, Swift Package, or monorepo).
  - Minimal reproducible example or code snippet.
  - Output of `changeblast doctor`.
