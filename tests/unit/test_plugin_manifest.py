"""Unit tests verifying Claude Code plugin structure, manifests, skills, and commands."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


class TestClaudeCodePluginStructure:
    """Validate plugin.json, marketplace.json, skills, commands, and workflows."""

    def test_plugin_json_manifest_valid(self) -> None:
        plugin_json = WORKSPACE_ROOT / ".claude-plugin" / "plugin.json"
        assert plugin_json.exists()

        data = json.loads(plugin_json.read_text(encoding="utf-8"))
        assert data["name"] == "changeblast"
        assert data["version"] == "0.1.0"
        assert len(data["description"]) > 20
        assert "author" in data
        assert "license" in data
        assert "keywords" in data
        assert "android" in data["keywords"]
        assert "ios" in data["keywords"]

    def test_marketplace_json_manifest_valid(self) -> None:
        marketplace_json = WORKSPACE_ROOT / ".claude-plugin" / "marketplace.json"
        assert marketplace_json.exists()

        data = json.loads(marketplace_json.read_text(encoding="utf-8"))
        assert data["name"] == "changeblast"
        assert "owner" in data
        assert "plugins" in data
        assert any(p["name"] == "changeblast" for p in data["plugins"])

    def test_skill_markdown_valid(self) -> None:
        skill_file = WORKSPACE_ROOT / "skills" / "changeblast" / "SKILL.md"
        assert skill_file.exists()

        content = skill_file.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "name: changeblast" in content
        assert "description:" in content
        assert "Strict Read-Only & Safety Invariant" in content
        assert "Workflow Decision Tree" in content
        assert "Engine Discovery & Invocation" in content
        assert "Interpretation Rules: Severity vs. Confidence" in content

    def test_progressive_disclosure_workflows_exist(self) -> None:
        workflows_dir = WORKSPACE_ROOT / "skills" / "changeblast" / "workflows"
        expected_workflows = [
            "setup.md",
            "analyze.md",
            "diff.md",
            "commit.md",
            "pr.md",
            "parity.md",
            "investigate.md",
        ]
        for wf in expected_workflows:
            wf_path = workflows_dir / wf
            assert wf_path.exists(), f"Missing workflow: {wf}"
            assert len(wf_path.read_text(encoding="utf-8").strip()) > 100

    def test_progressive_disclosure_references_exist(self) -> None:
        references_dir = WORKSPACE_ROOT / "skills" / "changeblast" / "references"
        expected_refs = [
            "android_heuristics.md",
            "ios_heuristics.md",
            "risk_and_confidence.md",
            "json_schema.md",
            "static_analysis_limits.md",
        ]
        for ref in expected_refs:
            ref_path = references_dir / ref
            assert ref_path.exists(), f"Missing reference: {ref}"
            assert len(ref_path.read_text(encoding="utf-8").strip()) > 100

    def test_templates_exist(self) -> None:
        templates_dir = WORKSPACE_ROOT / "skills" / "changeblast" / "templates"
        expected_templates = [
            "pr_impact_summary.md",
            "risk_disclosure.md",
            "investigation_report.md",
        ]
        for tpl in expected_templates:
            tpl_path = templates_dir / tpl
            assert tpl_path.exists(), f"Missing template: {tpl}"
            assert len(tpl_path.read_text(encoding="utf-8").strip()) > 100

    def test_developer_slash_commands_exist(self) -> None:
        commands_dir = WORKSPACE_ROOT / "commands"
        expected_commands = [
            "changeblast.md",
            "setup.md",
            "analyze.md",
            "diff.md",
            "commit.md",
            "pr.md",
            "parity.md",
            "investigate.md",
        ]
        for cmd in expected_commands:
            cmd_path = commands_dir / cmd
            assert cmd_path.exists(), f"Missing command: {cmd}"
            text = cmd_path.read_text(encoding="utf-8")
            assert text.startswith("---"), f"Command {cmd} missing YAML frontmatter"
            assert "description:" in text

    @pytest.mark.skipif(shutil.which("claude") is None, reason="Claude CLI not in PATH")
    def test_claude_cli_validation(self) -> None:
        result = subprocess.run(
            ["claude", "plugin", "validate", "--strict", str(WORKSPACE_ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"Claude plugin validation failed: {result.stdout}\n{result.stderr}"
        )
        assert "Validation passed" in result.stdout
