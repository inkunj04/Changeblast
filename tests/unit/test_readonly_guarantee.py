"""Verification tests enforcing the strict read-only execution invariant."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from changeblast.adapters.git import GitAdapter
from changeblast.adapters.parsers import (
    JavaParserAdapter,
    KotlinParserAdapter,
    SwiftParserAdapter,
)
from changeblast.discovery import discover_repository


def calculate_workspace_hashes(root: Path) -> dict[str, str]:
    """Calculate cryptographic SHA256 hashes of all non-git files in workspace."""
    hashes: dict[str, str] = {}
    for p in sorted(root.glob("**/*")):
        if p.is_file() and ".git" not in p.parts:
            rel = str(p.relative_to(root)).replace("\\", "/")
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


def get_git_status(root: Path) -> str:
    """Retrieve raw porcelain git status."""
    proc = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


class TestReadOnlyGuarantee:
    """Rigorous verification that ChangeBlast operations NEVER modify analyzed repository state."""

    def test_analysis_preserves_workspace_hashes_and_git_status(self, temp_workspace: Path) -> None:
        # 1. Setup realistic mixed Android/iOS repository
        subprocess.run(["git", "-C", str(temp_workspace), "init", "-b", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.name", "Audit"], check=True
        )
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.email", "audit@changeblast.org"],
            check=True,
        )

        android_dir = temp_workspace / "android/src/main/kotlin"
        android_dir.mkdir(parents=True, exist_ok=True)
        kt_file = android_dir / "UserAuth.kt"
        kt_file.write_text(
            "package com.example\nclass UserAuth {\n    fun login() = true\n}\n",
            encoding="utf-8",
        )

        ios_dir = temp_workspace / "ios/Sources"
        ios_dir.mkdir(parents=True, exist_ok=True)
        swift_file = ios_dir / "App.swift"
        swift_file.write_text(
            'import SwiftUI\nstruct App: View {\n    var body: some View { Text("App") }\n}\n',
            encoding="utf-8",
        )

        subprocess.run(["git", "-C", str(temp_workspace), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "commit", "-m", "Initial commit"], check=True
        )

        # Introduce uncommitted change
        kt_file.write_text(
            "package com.example\nclass UserAuth {\n    fun login() = false\n    fun logout() {}\n}\n",
            encoding="utf-8",
        )

        # 2. Capture baseline hashes and git status BEFORE analysis
        hashes_before = calculate_workspace_hashes(temp_workspace)
        status_before = get_git_status(temp_workspace)

        assert len(hashes_before) > 0
        assert "M android/src/main/kotlin/UserAuth.kt" in status_before

        # 3. Execute all discovery, git extraction, and parsing operations
        profile = discover_repository(temp_workspace)
        assert len(profile.platforms) == 2

        git_adapter = GitAdapter(temp_workspace)
        changeset = git_adapter.get_changeset()
        assert len(changeset.changed_files) == 1

        parsers = [KotlinParserAdapter(), JavaParserAdapter(), SwiftParserAdapter()]
        for cf in changeset.changed_files:
            target_path = temp_workspace / cf.path
            content = target_path.read_bytes()
            for p in parsers:
                if p.can_parse(target_path):
                    _ = p.parse_symbols(target_path, content)
                    _ = p.extract_dependencies(target_path, content)

        # 4. Capture hashes and git status AFTER analysis
        hashes_after = calculate_workspace_hashes(temp_workspace)
        status_after = get_git_status(temp_workspace)

        # 5. Strict Assertions: Zero byte differences, zero git status discrepancies
        assert hashes_before == hashes_after, "File hashes mutated during analysis!"
        assert status_before == status_after, "Git status changed during analysis!"
