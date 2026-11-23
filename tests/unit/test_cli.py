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
        import subprocess

        subprocess.run(["git", "-C", str(temp_workspace), "init", "-b", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.name", "Test"], check=True
        )
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.email", "test@example.com"],
            check=True,
        )

        test_file = temp_workspace / "App.kt"
        test_file.write_text("class App { fun start() = true }\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(temp_workspace), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "commit", "-m", "Initial commit"], check=True
        )

        exit_code = main(["analyze", "--repo", str(temp_workspace)])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "ChangeBlast Changeset Analysis" in captured.out

    def test_cli_profile_text_format(
        self, temp_workspace: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (temp_workspace / "build.gradle.kts").touch()
        exit_code = main(["profile", "--repo", str(temp_workspace), "--format", "summary"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "ChangeBlast Workspace Profile" in captured.out
        assert "Platforms: android" in captured.out

    def test_cli_analyze_json_format_with_changes(
        self, temp_workspace: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import subprocess

        subprocess.run(["git", "-C", str(temp_workspace), "init", "-b", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.name", "Test"], check=True
        )
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.email", "test@example.com"],
            check=True,
        )

        test_file = temp_workspace / "App.kt"
        test_file.write_text("class App { fun start() = true }\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(temp_workspace), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "commit", "-m", "Initial commit"], check=True
        )

        # Introduce uncommitted change
        test_file.write_text("class App { fun start() = false; fun stop() {} }\n", encoding="utf-8")

        exit_code = main(["analyze", "--repo", str(temp_workspace), "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["schema_version"] == CURRENT_SCHEMA_VERSION
        assert data["extracted_symbols_count"] >= 1
        assert len(data["changeset"]["changed_files"]) == 1

    def test_cli_invalid_repo_path_returns_error_code(self) -> None:
        exit_code = main(["analyze", "--repo", "/non/existent/path/for/sure"])
        assert exit_code == 2
