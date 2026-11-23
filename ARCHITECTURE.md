# ChangeBlast: System Architecture & Component Specification

ChangeBlast is a production-quality, open-source mobile change-impact intelligence tool. It analyzes source code changes in native Android (Kotlin, Java) and native iOS (Swift) projects, extracts symbol-level diffs, traverses call and dependency graphs, and calculates the exact blast radius and risk score of changes—all without executing user code, requiring compilers, or invoking external AI APIs.

The final product is packaged and distributed as a **Claude Code Plugin**, backed by a fast, deterministic **Python Analysis Engine**.

---

## 1. Architectural Philosophy & Principles

ChangeBlast adheres strictly to **Clean Architecture** and **Hexagonal Architecture (Ports and Adapters)**:

1. **Inward Dependency Rule**: Domain entities and business use cases have zero dependencies on external frameworks, database drivers, AST libraries, or CLI tools.
2. **Deterministic & Offline**: The Python analysis engine executes 100% locally. It uses Tree-sitter AST queries and graph algorithms. No external AI APIs, cloud services, or network calls exist in the engine.
3. **Strictly Read-Only**: The engine performs zero write operations to the analyzed codebase. It never compiles code, never generates bytecode, and never executes project build systems (e.g., Gradle, Xcode, CMake).
4. **Resilient AST Parsing**: Mobile code being analyzed is often uncommitted, broken, or mid-refactor. Tree-sitter's error-tolerant incremental parser guarantees robust symbol extraction even in syntax-error states.
5. **Decoupled Claude Code Integration**: The Python engine provides a standalone, machine-readable CLI interface (`changeblast analyze --format json`). The Claude Code plugin is an autonomous client that triggers the CLI, interprets the JSON report, and drives AI-assisted code review.

```
+-----------------------------------------------------------------------------------+
|                              Claude Code Plugin                                   |
|   Slash Commands (/changeblast:blast)  |  Mobile Change Impact Agent Skills       |
+---------------------------------------------------------+-------------------------+
                                                          | invokes via CLI (JSON)
                                                          v
+-----------------------------------------------------------------------------------+
|                        ChangeBlast Python Engine (CLI)                            |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                 Adapters Layer (Infrastructure & Presentation)              |  |
|  |   GitCliAdapter    TreeSitterParserAdapter    TyperCliAdapter   JsonAdapter |  |
|  +-----------------------------------------------------------------------------+  |
|                                         | implements ports                        |
|                                         v                                         |
|  +-----------------------------------------------------------------------------+  |
|  |                           Ports Layer (Interfaces)                          |  |
|  |   IGitDiffProvider   IAstParserPort   ISymbolIndexer   IImpactAnalyzerPort  |  |
|  +-----------------------------------------------------------------------------+  |
|                                         | invoked by                              |
|                                         v                                         |
|  +-----------------------------------------------------------------------------+  |
|  |                         Application Use Cases Layer                         |  |
|  |   AnalyzeImpactUseCase   IndexSymbolsUseCase   CalculateRiskUseCase         |  |
|  +-----------------------------------------------------------------------------+  |
|                                         | operates on                             |
|                                         v                                         |
|  +-----------------------------------------------------------------------------+  |
|  |                         Domain Entities & Value Objects                     |  |
|  |   Symbol    FileDiff    CallEdge    ImpactGraph    BlastRadius   RiskScore  |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Component Architecture & Layer Decomposition

### 2.1 Domain Core (`changeblast.core.domain`)

The domain core defines pure immutable business models representing mobile code concepts:

- **`Language`**: Enum (`KOTLIN`, `JAVA`, `SWIFT`).
- **`SymbolKind`**: Enum (`CLASS`, `INTERFACE`, `STRUCT`, `ENUM`, `FUNCTION`, `METHOD`, `PROPERTY`, `VARIABLE`, `ANNOTATION`).
- **`Visibility`**: Enum (`PUBLIC`, `PROTECTED`, `INTERNAL`, `PRIVATE`, `PACKAGE_PRIVATE`).
- **`SourceLocation`**: Value object with `file_path`, `start_line`, `start_col`, `end_line`, `end_col`.
- **`Symbol`**: Unified declaration entity:
  - `id`: Fully qualified or deterministic URI (e.g., `kt://com.example.app.AuthManager#login`).
  - `name`: Identifier string.
  - `kind`: `SymbolKind`.
  - `visibility`: `Visibility`.
  - `location`: `SourceLocation`.
  - `container`: Parent symbol ID (for nested methods/classes).
  - `annotations`: List of applied annotations/attributes (e.g., `@Composable`, `@GET`, `@Binding`, `@MainActor`).
- **`FileDiff`**: Unified representation of a changed file:
  - `path`: Target file path.
  - `old_path`: Original path if renamed.
  - `change_type`: `ADDED`, `MODIFIED`, `DELETED`, `RENAMED`.
  - `changed_line_ranges`: Tuple of `(start_line, end_line)`.
- **`CallEdge`**: Relationship between symbols:
  - `caller_id`: Originating symbol ID.
  - `callee_id`: Target symbol ID.
  - `edge_kind`: `CALLS`, `OVERRIDES`, `IMPLEMENTS`, `EXTENDS`, `REFERENCES`, `INSTANTIATES`.
  - `location`: Call site `SourceLocation`.
- **`ImpactedNode`**:
  - `symbol`: The impacted `Symbol`.
  - `depth`: Distance from direct modification (0 = directly modified, 1 = direct caller, 2+ = transitive).
  - `impact_path`: List of symbol IDs forming the reachability chain.
  - `is_ui_entry_point`: Boolean (Activity, Fragment, ViewController, SwiftUI View, Compose Screen).
  - `is_test_target`: Boolean (Unit or UI test method).
- **`RiskScore`**:
  - `level`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
  - `score`: Float `[0.0 - 100.0]`.
  - `reasons`: List of contributing deterministic factors.

---

### 2.2 Ports (Domain Interfaces) (`changeblast.core.ports`)

```python
from abc import ABC, abstractmethod
from typing import Sequence
from changeblast.core.domain.models import (
    AnalysisRequest,
    AnalysisReport,
    FileDiff,
    Symbol,
    CallEdge,
    ImpactGraph,
)

class IGitDiffPort(ABC):
    """Port for extracting diff information from the local repository."""
    @abstractmethod
    def get_diff(self, base_ref: str | None = None, target_ref: str | None = None) -> Sequence[FileDiff]:
        """Extract changed files and affected line ranges."""
        ...

class IAstParserPort(ABC):
    """Port for parsing source code into language-agnostic AST nodes."""
    @abstractmethod
    def parse_file(self, file_path: str, content: bytes) -> Sequence[Symbol]:
        """Extract symbol definitions from a source file."""
        ...

    @abstractmethod
    def extract_references(self, file_path: str, content: bytes) -> Sequence[CallEdge]:
        """Extract call sites, inheritance, and symbol references."""
        ...

class ISymbolIndexerPort(ABC):
    """Port for maintaining an in-memory symbol registry across the codebase."""
    @abstractmethod
    def index_symbols(self, symbols: Sequence[Symbol]) -> None:
        ...

    @abstractmethod
    def find_symbol_by_location(self, file_path: str, line: int) -> Symbol | None:
        ...

    @abstractmethod
    def resolve_symbol(self, query: str, context_file: str) -> Symbol | None:
        ...

class IImpactAnalyzerPort(ABC):
    """Port for building dependency graphs and computing blast radius."""
    @abstractmethod
    def build_graph(self, symbols: Sequence[Symbol], edges: Sequence[CallEdge]) -> ImpactGraph:
        ...

    @abstractmethod
    def compute_impact(self, modified_symbols: Sequence[Symbol], graph: ImpactGraph) -> AnalysisReport:
        ...

class IReportRendererPort(ABC):
    """Port for formatting the analysis report."""
    @abstractmethod
    def render_json(self, report: AnalysisReport) -> str:
        ...

    @abstractmethod
    def render_markdown(self, report: AnalysisReport) -> str:
        ...
```

---

### 2.3 Application Use Cases (`changeblast.core.use_cases`)

1. **`AnalyzeChangeImpactUseCase`**:
   - Coordinates the pipeline:
     1. Retrieve git diff (`IGitDiffPort`).
     2. Identify modified source files matching supported languages (`.kt`, `.java`, `.swift`).
     3. Parse target files and workspace references (`IAstParserPort`).
     4. Build symbol table index (`ISymbolIndexerPort`).
     5. Correlate changed line ranges with AST nodes to identify **Directly Modified Symbols**.
     6. Construct the directed dependency/call graph (`IImpactAnalyzerPort`).
     7. Traverse upstream reverse-callers to compute transitive blast radius.
     8. Tag UI entry points and test targets.
     9. Compute deterministic Risk Score.
     10. Output `AnalysisReport`.

2. **`FilterByScopeUseCase`**:
   - Allows scoping impact to specific modules or test suites.

---

### 2.4 Adapters Layer (`changeblast.adapters`)

1. **`GitCliAdapter` (`changeblast.adapters.git`)**:
   - Executes read-only git commands via `subprocess.run`:
     - `git diff --unified=0 <base_ref>...<target_ref>`
     - `git status --porcelain` (for uncommitted changes)
   - Parses unified diff hunks into `FileDiff` and `(start_line, end_line)` ranges.
   - Enforces read-only execution: no staging, no commits, no checkouts.

2. **`TreeSitterParserAdapter` (`changeblast.adapters.parsers`)**:
   - Wraps `tree-sitter` with language grammars:
     - `tree_sitter_kotlin`: Kotlin queries for classes, functions, properties, companion objects.
     - `tree_sitter_java`: Java queries for classes, methods, fields, interfaces, annotations.
     - `tree_sitter_swift`: Swift queries for classes, structs, protocols, functions, extensions.
   - Converts Tree-sitter `Node` objects into domain `Symbol` and `CallEdge` value objects.

3. **`NetworkXGraphAdapter` (`changeblast.adapters.graph`)**:
   - Manages a directed multigraph (`networkx.MultiDiGraph`) in memory.
   - Uses reverse breadth-first traversal (`bfs_edges` on reversed graph) to find callers up to configurable maximum depth.
   - Bounded recursion protects against circular dependencies and infinite recursion.

4. **`TyperCliAdapter` (`changeblast.adapters.cli`)**:
   - Entry point: `changeblast analyze [OPTIONS]`.
   - Flags: `--ref <git-ref>`, `--format [json|markdown|rich]`, `--max-depth <int>`, `--min-risk [low|med|high]`.

---

## 3. Component Contracts & Data Schemas

All contracts are defined with strict Pydantic v2 schemas:

```python
from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, ConfigDict

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SymbolKind(str, Enum):
    CLASS = "CLASS"
    INTERFACE = "INTERFACE"
    STRUCT = "STRUCT"
    ENUM = "ENUM"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    PROPERTY = "PROPERTY"
    VARIABLE = "VARIABLE"
    ANNOTATION = "ANNOTATION"

class Visibility(str, Enum):
    PUBLIC = "PUBLIC"
    PROTECTED = "PROTECTED"
    INTERNAL = "INTERNAL"
    PRIVATE = "PRIVATE"
    PACKAGE_PRIVATE = "PACKAGE_PRIVATE"

class SourceLocation(BaseModel):
    model_config = ConfigDict(frozen=True)
    file_path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int

class SymbolSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(description="Deterministic URI representing symbol")
    name: str
    kind: SymbolKind
    visibility: Visibility
    location: SourceLocation
    container_id: Optional[str] = None
    annotations: List[str] = Field(default_factory=list)

class ImpactedSymbolSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: SymbolSchema
    depth: int = Field(description="0=directly modified, 1=direct dependent, 2+=transitive")
    impact_path: List[str] = Field(description="Symbol ID trail from root change")
    is_ui_entry_point: bool = False
    is_test_target: bool = False

class RiskAssessmentSchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    level: RiskLevel
    score: float = Field(ge=0.0, le=100.0)
    reasons: List[str]
    breaking_change_signals: List[str]

class BlastRadiusSummarySchema(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_files_changed: int
    directly_modified_symbols: int
    direct_dependents_count: int
    transitive_dependents_count: int
    impacted_ui_components_count: int
    recommended_test_targets_count: int

class AnalysisReportSchema(BaseModel):
    """Top-level contract serialized to JSON for Claude Code and external tooling."""
    model_config = ConfigDict(frozen=True)
    version: str = "1.0.0"
    target_ref: str
    summary: BlastRadiusSummarySchema
    risk: RiskAssessmentSchema
    modified_symbols: List[SymbolSchema]
    impacted_symbols: List[ImpactedSymbolSchema]
    recommended_tests: List[str]
```

---

## 4. Deterministic Risk Assessment Model

Risk scoring is computed strictly through transparent heuristics without non-deterministic AI variance:

| Factor | Weight | Condition |
| :--- | :--- | :--- |
| **Public API Modification** | +25 pts | Changing signature/visibility of `public` / `open` symbol |
| **Core Architecture Impact** | +20 pts | Modifying symbols inherited by > 5 classes or widely imported |
| **Transitive Depth ($\ge 3$)**| +15 pts | Blast radius spans 3 or more layers of callers |
| **UI Entry Point Exposure** | +20 pts | Impacts Android Activity/Fragment/Compose or iOS UIViewController/SwiftUI |
| **Missing Test Coverage** | +20 pts | Zero detected test targets calling the modified symbol |
| **Low Blast Scope** | -20 pts | Change is `private` with 0 external dependents |

**Thresholds**:
- `0.0 - 24.9`: **LOW** (Safe for fast merge, localized impact)
- `25.0 - 49.9`: **MEDIUM** (Standard PR review, requires targeted test execution)
- `50.0 - 74.9`: **HIGH** (Cross-module blast radius, multi-layer verification needed)
- `75.0 - 100.0`: **CRITICAL** (Core architectural change or public contract breakage)

---

## 5. Security & Read-Only Invariants

1. **Subprocess Sandboxing**: All `git` commands use explicit argument lists (no `shell=True`) to prevent shell injection.
2. **Filesystem Boundary**: Resolves symlinks and validates that all inspected paths reside within the Git repository root (preventing directory traversal attacks like `../../etc/passwd`).
3. **Zero Network Connectivity**: No outbound HTTP requests or network sockets are opened during analysis.
4. **No Dynamic Code Evaluation**: Code is inspected exclusively via Tree-sitter concrete syntax trees. No `eval()`, `exec()`, or dynamic class loading.
