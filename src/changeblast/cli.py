"""ChangeBlast Command Line Interface.

Provides CLI commands built exclusively with the standard library `argparse`
module, ensuring zero runtime dependencies for the CLI entry point.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from changeblast.adapters.git import GitAdapter
from changeblast.adapters.graph import InMemoryDependencyGraph
from changeblast.adapters.parsers import JavaParserAdapter, KotlinParserAdapter, SwiftParserAdapter
from changeblast.adapters.reporters import ReportFormatter
from changeblast.analysis import ImpactAnalyzer
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
                syms = p.parse_symbols(file_path, content)
                for sym in syms:
                    graph.add_symbol(sym)
                edges = p.extract_dependencies(file_path, content)
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
