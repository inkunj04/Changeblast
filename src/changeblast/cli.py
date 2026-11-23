"""ChangeBlast Command Line Interface.

Provides CLI commands built exclusively with the standard library `argparse`
module, ensuring zero runtime dependencies for the CLI entry point.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from changeblast.adapters.git import GitAdapter
from changeblast.adapters.graph import InMemoryDependencyGraph
from changeblast.adapters.parsers import JavaParserAdapter, KotlinParserAdapter, SwiftParserAdapter
from changeblast.adapters.reporters import ReportFormatter
from changeblast.analysis import ImpactAnalyzer, SymbolDiffCorrelator
from changeblast.analysis.mobile import CrossPlatformCorrelator
from changeblast.discovery import discover_repository
from changeblast.exceptions import (
    ChangeBlastError,
    CliArgumentError,
    SecurityBoundaryViolationError,
)
from changeblast.logging import get_logger, setup_logging
from changeblast.models import (
    CURRENT_SCHEMA_VERSION,
    AnalysisWarning,
    ChangeSet,
    DependencyEdge,
    EvidenceReference,
    ImpactFinding,
    ImpactReport,
    Platform,
    RepositoryProfile,
    SourceSymbol,
    get_schema_for_model,
)
from changeblast.version import __version__

# Map model names to model classes for schema extraction
SCHEMA_MODEL_MAP: dict[str, type[BaseModel]] = {
    "report": ImpactReport,
    "repository": RepositoryProfile,
    "changeset": ChangeSet,
    "symbol": SourceSymbol,
    "edge": DependencyEdge,
    "evidence": EvidenceReference,
    "finding": ImpactFinding,
    "warning": AnalysisWarning,
}


def build_parser() -> argparse.ArgumentParser:
    """Construct and configure the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="changeblast",
        description="Deterministic mobile change-impact intelligence for Android and iOS.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__} (schema v{CURRENT_SCHEMA_VERSION})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed debug logging.",
    )
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Format logs as structured JSON lines.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: analyze
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run change-impact analysis against uncommitted changes or git references.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    analyze_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Target repository path.",
    )
    analyze_parser.add_argument(
        "--base",
        dest="base_ref",
        type=str,
        default=None,
        help="Base git reference (commit, branch, or tag).",
    )
    analyze_parser.add_argument(
        "--target",
        dest="target_ref",
        type=str,
        default=None,
        help="Target git reference (defaults to working tree).",
    )
    analyze_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["summary", "json", "markdown"],
        default="summary",
        help="Output serialization format.",
    )
    analyze_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Destination file to write the report (defaults to stdout).",
    )
    analyze_parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="Maximum traversal depth for transitive dependency search.",
    )
    analyze_parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Filter impact analysis to a specific symbol name or pattern.",
    )

    # Command: doctor
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Verify Python environment, Tree-sitter parsers, and Git repository readiness.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    doctor_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Target repository path.",
    )
    doctor_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["summary", "json"],
        default="summary",
        help="Output serialization format.",
    )

    # Command: diff
    diff_parser = subparsers.add_parser(
        "diff",
        help="Inspect symbol-level AST changes and affected line ranges.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    diff_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Target repository path.",
    )
    diff_parser.add_argument(
        "--base",
        dest="base_ref",
        type=str,
        default=None,
        help="Base git reference.",
    )
    diff_parser.add_argument(
        "--target",
        dest="target_ref",
        type=str,
        default=None,
        help="Target git reference.",
    )
    diff_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["summary", "json"],
        default="summary",
        help="Output serialization format.",
    )

    # Command: parity
    parity_parser = subparsers.add_parser(
        "parity",
        help="Inspect cross-platform feature correspondences between Android and iOS.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parity_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Target repository path.",
    )
    parity_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["summary", "json"],
        default="summary",
        help="Output serialization format.",
    )

    # Command: schema
    schema_parser = subparsers.add_parser(
        "schema",
        help="Export JSON Schema definitions for ChangeBlast contracts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    schema_parser.add_argument(
        "--model",
        choices=["all", *list(SCHEMA_MODEL_MAP.keys())],
        default="all",
        help="Which model schema to export.",
    )
    schema_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Destination file to write the schema JSON (defaults to stdout).",
    )

    # Command: profile
    profile_parser = subparsers.add_parser(
        "profile",
        help="Detect mobile platforms, languages, and source roots in a workspace.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    profile_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Target repository path.",
    )
    profile_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["summary", "json"],
        default="summary",
        help="Output serialization format.",
    )

    return parser


def handle_schema_command(args: argparse.Namespace) -> int:
    """Handle the `schema` subcommand to export JSON schema definitions."""
    if args.model == "all":
        exported: dict[str, object] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "version": CURRENT_SCHEMA_VERSION,
            "models": {name: get_schema_for_model(cls) for name, cls in SCHEMA_MODEL_MAP.items()},
        }
    else:
        model_cls = SCHEMA_MODEL_MAP[args.model]
        exported = get_schema_for_model(model_cls)

    formatted_json = json.dumps(exported, indent=2)

    if args.output:
        dest_path = args.output.resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(formatted_json, encoding="utf-8")
        logger = get_logger("cli")
        logger.info(f"Schema written to {dest_path}")
    else:
        print(formatted_json)

    return 0


def handle_profile_command(args: argparse.Namespace) -> int:
    """Inspect repository profile using repository intelligence scanner."""
    repo_path = args.repo.resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise CliArgumentError(f"Repository path does not exist or is not a directory: {repo_path}")

    profile = discover_repository(repo_path)

    if args.output_format == "json":
        print(profile.model_dump_json(indent=2))
    else:
        print(f"ChangeBlast Workspace Profile: {profile.root_path}")
        platforms_str = (
            ", ".join(str(p.value if hasattr(p, "value") else p) for p in profile.platforms)
            if profile.platforms
            else "None detected"
        )
        print(f"  Platforms: {platforms_str} (Monorepo: {profile.is_monorepo})")
        langs_str = (
            ", ".join(
                str(lang.value if hasattr(lang, "value") else lang) for lang in profile.languages
            )
            if profile.languages
            else "None detected"
        )
        print(f"  Languages: {langs_str}")
        print(f"  Gradle Modules: {len(profile.gradle_modules)}")
        for gm in profile.gradle_modules:
            print(f"    - {gm.name} ({gm.path})")
        print(f"  Xcode Projects: {len(profile.xcode_projects)}")
        for xp in profile.xcode_projects:
            print(f"    - {xp.name} ({xp.path})")
        print(f"  Swift Packages: {len(profile.swift_packages)}")
        for sp in profile.swift_packages:
            print(f"    - {sp.name} ({sp.path})")
        print(f"  Source Roots: {len(profile.source_roots)}")
        print(f"  Test Roots: {len(profile.test_roots)}")
        if profile.vcs:
            print(
                f"  VCS: {profile.vcs.vcs_type} (branch: {profile.vcs.branch}, dirty: {profile.vcs.is_dirty})"
            )
    return 0


def handle_analyze_command(args: argparse.Namespace) -> int:
    """Execute Git changeset extraction, graph construction, and impact analysis."""
    logger = get_logger("cli")
    repo_path = args.repo.resolve()

    if not repo_path.exists() or not repo_path.is_dir():
        raise CliArgumentError(f"Target repository path is invalid: {repo_path}")

    # 1. Discover repository topology
    profile = discover_repository(repo_path)

    # 2. Extract Git changeset
    git_adapter = GitAdapter(repo_path)
    changeset = git_adapter.get_changeset(
        base_ref=args.base_ref,
        target_ref=args.target_ref,
    )

    # 3. Construct in-memory dependency graph
    graph = InMemoryDependencyGraph()
    for gm in profile.gradle_modules:
        graph.add_module(gm.name, gm.source_roots)
    for xp in profile.xcode_projects:
        graph.add_module(xp.name, [xp.path])
    for sp in profile.swift_packages:
        graph.add_module(sp.name, [sp.path])

    parsers = [KotlinParserAdapter(), JavaParserAdapter(), SwiftParserAdapter()]

    # Collect source files to parse
    scanned_files: set[Path] = set()
    for cf in changeset.changed_files:
        cf_path = repo_path / cf.path
        if cf_path.is_file():
            scanned_files.add(cf_path)

    for sroot in profile.source_roots:
        root_dir = repo_path / sroot
        if root_dir.is_dir():
            for p in root_dir.rglob("*"):
                if p.is_file() and p.suffix in {".kt", ".kts", ".java", ".swift"}:
                    scanned_files.add(p)

    for file_path in sorted(scanned_files):
        rel_str = str(file_path.relative_to(repo_path)).replace("\\", "/")
        graph.add_file(rel_str)
        for p in parsers:
            if p.can_parse(file_path):
                content = file_path.read_bytes()
                syms = p.parse_symbols(Path(rel_str), content)
                for sym in syms:
                    graph.add_symbol(sym)
                edges = p.extract_dependencies(Path(rel_str), content)
                for edge in edges:
                    graph.add_edge(edge)
                break

    logger.info(
        f"Built dependency graph with {graph.node_count} nodes and {graph.edge_count} edges."
    )

    # 4. Perform impact analysis
    analyzer = ImpactAnalyzer()
    report = analyzer.analyze(
        profile=profile,
        changeset=changeset,
        graph=graph,
        max_depth=args.max_depth,
    )

    # Optional symbol filter
    if getattr(args, "symbol", None):
        sym_pattern = args.symbol.lower()
        filtered_findings = [
            f
            for f in report.findings
            if sym_pattern in f.target_symbol.name.lower()
            or sym_pattern in f.root_changed_symbol_id.lower()
            or any(sym_pattern in p.lower() for p in f.propagation_path)
        ]
        updated_summary = report.summary.model_copy(
            update={"direct_impacts_count": len(filtered_findings)}
        )
        report = report.model_copy(
            update={"findings": filtered_findings, "summary": updated_summary}
        )

    # 5. Format and deliver report
    formatter = ReportFormatter()
    if args.output_format == "json":
        output_text = formatter.format_json(report)
    elif args.output_format == "markdown":
        output_text = formatter.format_markdown(report)
    else:
        output_text = formatter.format_summary(report)

    if args.output:
        dest_path = args.output.resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(output_text, encoding="utf-8")
        logger.info(f"Impact report written to {dest_path}")
    else:
        print(output_text)

    return 0


def handle_doctor_command(args: argparse.Namespace) -> int:
    """Verify host environment, Python version, Tree-sitter parsers, and Git readiness."""
    repo_path = args.repo.resolve()
    issues: list[str] = []

    # 1. Python version check
    py_ok = sys.version_info >= (3, 11)
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if not py_ok:
        issues.append(f"Python 3.11+ is required (found {py_version})")

    # 2. Git binary check
    git_version = "Not available"
    git_ok = False
    try:
        res = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            git_version = res.stdout.strip()
            git_ok = True
        else:
            issues.append("Git command returned non-zero exit code")
    except Exception as exc:
        issues.append(f"Git binary not found in PATH: {exc}")

    # 3. Tree-sitter parsers check
    parsers = {
        "kotlin": False,
        "java": False,
        "swift": False,
    }
    try:
        kp = KotlinParserAdapter()
        kp.parse_symbols(Path("Test.kt"), b"class Test")
        parsers["kotlin"] = True
    except Exception as exc:
        issues.append(f"Kotlin parser failed: {exc}")

    try:
        jp = JavaParserAdapter()
        jp.parse_symbols(Path("Test.java"), b"public class Test {}")
        parsers["java"] = True
    except Exception as exc:
        issues.append(f"Java parser failed: {exc}")

    try:
        sp = SwiftParserAdapter()
        sp.parse_symbols(Path("Test.swift"), b"class Test {}")
        parsers["swift"] = True
    except Exception as exc:
        issues.append(f"Swift parser failed: {exc}")

    # 4. Target repository check
    repo_info: dict[str, object] = {
        "path": str(repo_path),
        "exists": repo_path.is_dir(),
        "is_git": (repo_path / ".git").exists(),
    }
    if repo_path.is_dir():
        profile = discover_repository(repo_path)
        repo_info["platforms"] = [
            str(p.value if hasattr(p, "value") else p) for p in profile.platforms
        ]
        repo_info["languages"] = [
            str(lang.value if hasattr(lang, "value") else lang) for lang in profile.languages
        ]
        repo_info["gradle_modules"] = len(profile.gradle_modules)
        repo_info["xcode_projects"] = len(profile.xcode_projects)
        repo_info["swift_packages"] = len(profile.swift_packages)

    all_parsers_ok = all(parsers.values())
    status = "healthy" if (py_ok and git_ok and all_parsers_ok and not issues) else "degraded"

    result = {
        "status": status,
        "changeblast_version": __version__,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "python_version": py_version,
        "git_version": git_version,
        "tree_sitter_parsers": parsers,
        "repository": repo_info,
        "issues": issues,
    }

    if args.output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        status_icon = "✅" if status == "healthy" else "⚠️"
        print(f"{status_icon} ChangeBlast Engine Health: {status.upper()}")
        print(f"  Version: {__version__} (Schema v{CURRENT_SCHEMA_VERSION})")
        print(f"  Python: {py_version} ({'OK' if py_ok else 'FAIL'})")
        print(f"  Git: {git_version} ({'OK' if git_ok else 'FAIL'})")
        print("  Tree-sitter Grammars:")
        for lang, ok in parsers.items():
            print(f"    - {lang.capitalize()}: {'Ready' if ok else 'Error'}")
        print(f"  Repository: {repo_path}")
        platforms_val = repo_info.get("platforms", [])
        if isinstance(platforms_val, list):
            print(f"    - Platforms: {', '.join(platforms_val) if platforms_val else 'None'}")
        if issues:
            print("  Issues Encountered:")
            for issue in issues:
                print(f"    ⚠️  {issue}")

    return 0 if status == "healthy" else 1


def handle_diff_command(args: argparse.Namespace) -> int:
    """Inspect symbol-level AST changes and affected line ranges."""
    repo_path = args.repo.resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise CliArgumentError(f"Target repository path is invalid: {repo_path}")

    git_adapter = GitAdapter(repo_path)
    changeset = git_adapter.get_changeset(base_ref=args.base_ref, target_ref=args.target_ref)
    parsers = [KotlinParserAdapter(), JavaParserAdapter(), SwiftParserAdapter()]
    correlator = SymbolDiffCorrelator()

    graph = InMemoryDependencyGraph()
    for cf in changeset.changed_files:
        cf_path = repo_path / cf.path
        if not cf_path.is_file():
            continue
        rel_path = str(cf_path.relative_to(repo_path)).replace("\\", "/")
        graph.add_file(rel_path)
        for p in parsers:
            if p.can_parse(cf_path):
                content = cf_path.read_bytes()
                for sym in p.parse_symbols(Path(rel_path), content):
                    graph.add_symbol(sym)
                break

    modified_records = correlator.correlate(changeset, graph)

    if args.output_format == "json":
        data = {
            "base_ref": changeset.base_ref,
            "target_ref": changeset.target_ref,
            "total_files_changed": len(changeset.changed_files),
            "total_additions": changeset.total_additions,
            "total_deletions": changeset.total_deletions,
            "changed_files": [cf.model_dump() for cf in changeset.changed_files],
            "modified_symbols": [
                {
                    "name": rec.symbol.name,
                    "kind": (
                        rec.symbol.kind.value
                        if hasattr(rec.symbol.kind, "value")
                        else str(rec.symbol.kind)
                    ),
                    "file_path": rec.symbol.location.file_path,
                    "qualified_name": rec.symbol.qualified_name,
                    "start_line": rec.symbol.location.start_line,
                    "end_line": rec.symbol.location.end_line,
                    "is_entry_point": rec.symbol.is_entry_point,
                    "is_signature_modified": rec.is_signature_modified,
                    "is_deleted": rec.is_deleted,
                    "annotations": rec.symbol.annotations,
                }
                for rec in modified_records
            ],
        }
        print(json.dumps(data, indent=2))
    else:
        print(
            f"ChangeBlast Symbol Diff: {changeset.base_ref or 'HEAD~1'} -> {changeset.target_ref or 'Working Tree'}"
        )
        print(
            f"  Files Changed: {len(changeset.changed_files)} (+{changeset.total_additions}/-{changeset.total_deletions})"
        )
        print(f"  Modified Symbols: {len(modified_records)}")
        for rec in modified_records:
            sym = rec.symbol
            ep_flag = " [Entry Point]" if sym.is_entry_point else ""
            del_flag = " [DELETED]" if rec.is_deleted else ""
            sig_flag = " [Sig Changed]" if rec.is_signature_modified else ""
            kind_str = sym.kind.value if hasattr(sym.kind, "value") else str(sym.kind)
            print(
                f"    - `{sym.name}` ({kind_str}) in {sym.location.file_path}:{sym.location.start_line}-{sym.location.end_line}{ep_flag}{del_flag}{sig_flag}"
            )
    return 0


def handle_parity_command(args: argparse.Namespace) -> int:
    """Inspect cross-platform feature parity and architectural correspondences."""
    repo_path = args.repo.resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise CliArgumentError(f"Target repository path is invalid: {repo_path}")

    profile = discover_repository(repo_path)
    parsers = [KotlinParserAdapter(), JavaParserAdapter(), SwiftParserAdapter()]

    android_symbols: list[SourceSymbol] = []
    ios_symbols: list[SourceSymbol] = []

    for sroot in profile.source_roots:
        root_dir = repo_path / sroot
        if not root_dir.is_dir():
            continue
        for p in root_dir.rglob("*"):
            if not p.is_file():
                continue
            for parser in parsers:
                if parser.can_parse(p):
                    content = p.read_bytes()
                    syms = parser.parse_symbols(p, content)
                    if p.suffix in {".kt", ".kts", ".java"}:
                        android_symbols.extend(syms)
                    elif p.suffix == ".swift":
                        ios_symbols.extend(syms)
                    break

    android_findings = [
        ImpactFinding(
            finding_id=f"find_{s.id}",
            target_symbol=s,
            root_changed_symbol_id=s.id,
            depth=0,
            platform=Platform.ANDROID,
        )
        for s in android_symbols
    ]
    ios_findings = [
        ImpactFinding(
            finding_id=f"find_{s.id}",
            target_symbol=s,
            root_changed_symbol_id=s.id,
            depth=0,
            platform=Platform.IOS,
        )
        for s in ios_symbols
    ]

    correlator = CrossPlatformCorrelator()
    correlations = correlator.correlate(android_findings, ios_findings)

    if args.output_format == "json":
        data = {
            "total_correlations": len(correlations),
            "correlations": [c.model_dump() for c in correlations],
            "disclaimer": "Behavioral divergence warning: Android and iOS architectures differ fundamentally; never assume identically named components share implementation parity.",
        }
        print(json.dumps(data, indent=2))
    else:
        print("ChangeBlast Cross-Platform Feature Parity")
        print(f"  Correlated Features: {len(correlations)}")
        for c in correlations:
            print(
                f"    - {c.feature_name} (Basis: {c.correlation_type}, Confidence: {c.confidence.value})"
            )
            print(f"        Android: {c.android_symbol_id.split('//')[-1]}")
            print(f"        iOS:     {c.ios_symbol_id.split('//')[-1]}")
            print(f"        Notes:   {c.notes}")
        if not correlations:
            print("  _No shared cross-platform feature correspondences detected._")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point with structured error handling and return codes."""
    parser = build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level, json_format=args.json_logs)
    logger = get_logger("cli")

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "schema":
            return handle_schema_command(args)
        elif args.command == "profile":
            return handle_profile_command(args)
        elif args.command == "doctor":
            return handle_doctor_command(args)
        elif args.command == "diff":
            return handle_diff_command(args)
        elif args.command == "parity":
            return handle_parity_command(args)
        elif args.command == "analyze":
            return handle_analyze_command(args)
        else:
            parser.print_help()
            return 0
    except SecurityBoundaryViolationError as exc:
        logger.error(f"Security violation: {exc.message}", extra={"context": exc.details})
        return 3
    except CliArgumentError as exc:
        logger.error(f"Invalid argument: {exc.message}")
        return 2
    except ChangeBlastError as exc:
        logger.error(f"ChangeBlast error [{exc.__class__.__name__}]: {exc.message}")
        return 1
    except Exception as exc:
        logger.exception(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
