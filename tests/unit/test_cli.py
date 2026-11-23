"""Unit tests for ChangeBlast CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from changeblast.cli import main
from changeblast.models import CURRENT_SCHEMA_VERSION


class TestCli:
    """Validate command line parsing, subcommands, formatting, and exit codes."""

    def test_cli_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert f"schema v{CURRENT_SCHEMA_VERSION}" in captured.out

    def test_cli_no_args_prints_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main([])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert (
            "usage: changeblast" in captured.out
            or "Deterministic mobile change-impact" in captured.out
        )

    def test_cli_schema_export_all_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["schema"])
        assert exit_code == 0
        captured = capsys.readouterr()
        schema_dict = json.loads(captured.out)
        assert schema_dict["version"] == CURRENT_SCHEMA_VERSION
        assert "models" in schema_dict
        assert "report" in schema_dict["models"]
        assert "symbol" in schema_dict["models"]

    def test_cli_schema_export_specific_file(self, temp_workspace: Path) -> None:
        out_file = temp_workspace / "report_schema.json"
        exit_code = main(["schema", "--model", "report", "-o", str(out_file)])
        assert exit_code == 0
        assert out_file.exists()
        schema_data = json.loads(out_file.read_text(encoding="utf-8"))
        assert "properties" in schema_data
        assert "findings" in schema_data["properties"]

    def test_cli_profile_command(
        self, temp_workspace: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Create an Android indicator
        (temp_workspace / "build.gradle.kts").touch()
        exit_code = main(["profile", "--repo", str(temp_workspace), "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "android" in data["platforms"]

    def test_cli_analyze_command(
        self, temp_workspace: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["analyze", "--repo", str(temp_workspace)])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Phase 1" in captured.out or "foundation" in captured.out

    def test_cli_invalid_repo_path_returns_error_code(self) -> None:
        exit_code = main(["analyze", "--repo", "/non/existent/path/for/sure"])
        assert exit_code == 2
