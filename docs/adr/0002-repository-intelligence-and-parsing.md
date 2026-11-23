# ADR 0002: Phase 2 Repository Intelligence, Git Engine, & Source Parsing

## Status
**Accepted** (2026-11-23)

## Context
ChangeBlast must extract repository topology, Git modifications, and AST declarations from native Android (Kotlin, Java) and native iOS (Swift) projects. This intelligence forms the raw input for subsequent dependency graph construction and impact analysis without mutating repository state or requiring external AI APIs.

## Decisions

### 1. Repository Discovery & Exclusion Engine
- Implemented `RepositoryScanner` and `discover_repository()` in `changeblast.discovery`:
  - **Android Discovery**: Detects Gradle modules (`settings.gradle[.kts]`, `build.gradle[.kts]`), `AndroidManifest.xml`, `android/` directory roots, and source directories (`src/main/kotlin`, `src/main/java`).
  - **iOS Discovery**: Detects Xcode projects (`*.xcodeproj`), workspace structures, targets (`project.pbxproj` PBXNativeTarget inspection), and Swift Package manifests (`Package.swift`).
  - **Monorepo & Mixed Support**: Classifies repositories as monorepos if multiple modules/projects or both Android and iOS platforms coexist.
  - **Cache & Artifact Exclusion**: Recursively skips `.gradle/`, `build/`, `DerivedData/`, `.build/`, `Pods/`, `Carthage/`, `.git/`, and virtual environments.
  - **Generated Code Detection**: Identifies generated sources by directory paths (e.g., `build/generated`, `kapt/`, `Apollo/`, `Dagger/`) and content headers (e.g., `@Generated`, `DO NOT EDIT`).

### 2. Pure Read-Only Git Engine
- Implemented `GitAdapter` implementing `IVcsAdapter`:
  - Extracts changesets across working tree uncommitted changes, staged changes, commit comparisons (`commitA..commitB`), and branch comparisons (`base...target`).
  - Parses unified diff hunks into explicit 1-indexed `LineRange` objects.
  - Tracks file additions, modifications, deletions, and renames (`similarity_index`).
  - Enforces path boundary verification preventing directory traversal attacks.
  - Guarantees 100% read-only operation: verified via cryptographic SHA-256 file hashing before and after analysis.

### 3. Concrete Tree-Sitter Adapters (Kotlin, Java, Swift)
- Implemented `KotlinParserAdapter`, `JavaParserAdapter`, and `SwiftParserAdapter` conforming to `ILanguageParserAdapter`:
  - Utilizes official C bindings: `tree-sitter`, `tree-sitter-kotlin`, `tree-sitter-java`, and `tree-sitter-swift`.
  - Extracts symbols: classes, structs, protocols, enums, functions, methods, constructors, fields, properties, annotations, and exact byte/line source locations.
  - Extracts preliminary dependency edges: `IMPORTS`, `EXTENDS`, `IMPLEMENTS`, `CALLS`, and `REFERENCES`.
  - Distinguishes UI entry points (`Activity`, `Fragment`, `Composable`, `View`, `UIViewController`) and test entities (`@Test`, `XCTestCase`).
  - Implements resilient error recovery for malformed syntax by introspecting Tree-sitter `ERROR` nodes to extract partial declarations without crashing.

### 4. Platform Adapters
- Implemented `AndroidPlatformAdapter` and `IOSPlatformAdapter` encapsulating platform-specific discovery, parsing delegation, and entry point classifications.

## Consequences
- High-performance, memory-efficient source parsing without full compiler installations (no `javac`, `kotlinc`, or `swiftc` needed).
- Full offline, deterministic behavior with zero network calls and zero file modifications.
