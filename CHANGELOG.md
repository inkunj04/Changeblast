# Changelog

All notable changes to the ChangeBlast project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-11-23

### Added
- **Core Analysis Engine**: Deterministic static change-impact analysis engine for native mobile applications.
- **AST Parsers**: Tree-sitter parsers for Kotlin (`.kt`, `.kts`), Java (`.java`), and Swift (`.swift`) extracting symbols, inheritance, invocations, and line coordinates.
- **Repository Intelligence**: Automatic scanner detecting Gradle multi-module Android projects, Xcode projects/workspaces, Swift packages, and mixed monorepos.
- **Safe Git Adapter**: Read-only Git diff extraction supporting working tree uncommitted changes, staged changes, commit comparisons, and branch comparisons.
- **In-Memory Dependency Graph**: Directed graph engine supporting file, symbol, module, and test nodes with iterative stack cycle detection and depth limiting.
- **Mobile Architectural Intelligence**:
  - Android analyzer covering 10 architectural domains (Activity/Fragment lifecycle, Compose recomposition, Navigation deep links, Permissions, Manifest, WorkManager, Room, Hilt DI, Retrofit networking, Play Billing).
  - iOS analyzer covering 10 architectural domains (UIViewController lifecycle, SwiftUI state, NavigationStack, App lifecycle, BGTaskScheduler, Universal Links, Core Data, Keychain, Swinject DI, StoreKit 2).
- **Cross-Platform Correlator**: Feature parity correlator matching Android and iOS implementations with explicit behavioral divergence warnings.
- **Dual-Axis Risk Engine**: Independent classification of impact Severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and static Confidence (`VERIFIED`, `STRONG_INFERENCE`, `POSSIBLE`, `UNKNOWN`).
- **Claude Code Plugin**: First-class plugin for Claude Code including:
  - Plugin manifest (`.claude-plugin/plugin.json`) and marketplace definition (`.claude-plugin/marketplace.json`).
  - Core intelligence skill (`skills/changeblast/SKILL.md`).
  - Slash commands: `/changeblast setup`, `/changeblast analyze`, `/changeblast diff`, `/changeblast commit`, `/changeblast pr`, `/changeblast parity`, `/changeblast investigate`.
- **Security & Read-Only Guarantees**: Cryptographic SHA-256 tree hashing verifying zero repository mutation, path traversal defenses, null-byte injection rejection, and zero network calls.
- **Command-Line Interface**: CLI commands for `analyze`, `diff`, `parity`, `doctor`, `profile`, `schema`, and `version`.
