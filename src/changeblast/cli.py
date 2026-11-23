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
    """Inspect repository profile without running dependency analysis."""
    repo_path = args.repo.resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise CliArgumentError(f"Repository path does not exist or is not a directory: {repo_path}")

    # Inspect directory structure for mobile indicators
    has_gradle = (
        any(repo_path.glob("build.gradle*")) or (repo_path / "settings.gradle.kts").exists()
    )
    has_xcode = (
        any(repo_path.glob("*.xcodeproj"))
        or any(repo_path.glob("*.xcworkspace"))
        or (repo_path / "Package.swift").exists()
    )

    platforms = []
    if has_gradle or (repo_path / "app/src/main").exists():
        platforms.append("android")
    if has_xcode:
        platforms.append("ios")

    profile_dict = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "root_path": str(repo_path),
        "platforms": platforms,
        "is_git_repository": (repo_path / ".git").is_dir(),
    }

    if args.output_format == "json":
        print(json.dumps(profile_dict, indent=2))
    else:
        print(f"ChangeBlast Workspace Profile: {repo_path}")
        print(f"  Platforms: {', '.join(platforms) if platforms else 'None detected'}")
        print(f"  Git Repository: {profile_dict['is_git_repository']}")
    return 0


def handle_analyze_command(args: argparse.Namespace) -> int:
    """Placeholder execution for analyze command during Phase 1."""
    logger = get_logger("cli")
    repo_path = args.repo.resolve()

    if not repo_path.exists() or not repo_path.is_dir():
        raise CliArgumentError(f"Target repository path is invalid: {repo_path}")

    logger.info(
        f"ChangeBlast Phase 1 Foundation: analyze invoked for {repo_path} "
        f"(base={args.base_ref}, target={args.target_ref}, format={args.output_format})"
    )
    print(
        "ChangeBlast engine foundation initialized. Full dependency analysis activates in Phase 2."
    )
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
