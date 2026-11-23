"""Security QA test suite verifying isolation, path traversal defense, and safety invariants."""

from __future__ import annotations

import hashlib
import os
import socket
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from changeblast.adapters.git import GitAdapter, validate_path_within_root
from changeblast.cli import main
from changeblast.discovery import discover_repository
from changeblast.exceptions import SecurityBoundaryViolationError


class TestSecurityQA:
    """Security verification suite ensuring zero compromise, leaks, or escapes."""

    def test_path_traversal_attempts_blocked(self, temp_workspace: Path) -> None:
        """Verify that relative, absolute, and escaped paths are blocked."""
        with pytest.raises(SecurityBoundaryViolationError):
            validate_path_within_root(temp_workspace, "../../etc/passwd")

        with pytest.raises(SecurityBoundaryViolationError):
            validate_path_within_root(temp_workspace, "../../../../../../../etc/shadow")

        with pytest.raises(SecurityBoundaryViolationError):
            validate_path_within_root(temp_workspace, "/etc/hosts")

    def test_null_byte_injection_blocked(self, temp_workspace: Path) -> None:
        """Verify that null byte injection attempts are rejected."""
        with pytest.raises(SecurityBoundaryViolationError):
            validate_path_within_root(temp_workspace, "app/src/main/App.kt\0/../../etc/passwd")

    def test_symlink_escaping_repository_root_blocked(
        self, temp_workspace: Path, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        """Verify that symlinks pointing outside the repository root are rejected."""
        outside_dir = tmp_path_factory.mktemp("outside_secrets")
        secret_file = outside_dir / "secret.env"
        secret_file.write_text("SUPER_SECRET_KEY=12345\n", encoding="utf-8")

        # Create symlink inside workspace pointing to outside secret file
        symlink_path = temp_workspace / "symlink_secret.kt"
        try:
            os.symlink(str(secret_file), str(symlink_path))
        except OSError:
            pytest.skip("Symlinks not supported on this filesystem")

        # Direct validation must fail
        with pytest.raises(SecurityBoundaryViolationError):
            validate_path_within_root(temp_workspace, "symlink_secret.kt")

        # Adapter content retrieval must refuse to read through escaping symlink
        subprocess.run(["git", "-C", str(temp_workspace), "init", "-b", "main"], check=True)
        git_adapter = GitAdapter(temp_workspace)
        with pytest.raises(SecurityBoundaryViolationError):
            git_adapter.get_file_content(temp_workspace, "symlink_secret.kt")

    def test_malicious_filenames_handled_safely(self, temp_workspace: Path) -> None:
        """Verify that filenames containing shell metacharacters cannot execute commands."""
        subprocess.run(["git", "-C", str(temp_workspace), "init", "-b", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.name", "SecurityTest"], check=True
        )
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.email", "sec@example.com"],
            check=True,
        )

        # File with dangerous metacharacters and flags (no path separator slashes)
        evil_file = temp_workspace / "test; rm -rf . ; $(whoami) --flag.kt"
        evil_file.write_text("class EvilApp { fun run() {} }\n", encoding="utf-8")

        subprocess.run(["git", "-C", str(temp_workspace), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "commit", "-m", "Commit with evil filename"],
            check=True,
        )

        # Modify it to generate diff
        evil_file.write_text("class EvilApp { fun run() { println() } }\n", encoding="utf-8")

        # Run analyze and diff commands - must succeed safely without command injection
        exit_code = main(["analyze", "--repo", str(temp_workspace), "--format", "json"])
        assert exit_code == 0

        diff_exit_code = main(["diff", "--repo", str(temp_workspace), "--format", "json"])
        assert diff_exit_code == 0

    def test_strict_read_only_and_hash_integrity(self, temp_workspace: Path) -> None:
        """Verify that ChangeBlast leaves workspace and Git state 100% byte-for-byte untouched."""
        subprocess.run(["git", "-C", str(temp_workspace), "init", "-b", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.name", "Test"], check=True
        )
        subprocess.run(
            ["git", "-C", str(temp_workspace), "config", "user.email", "test@example.com"],
            check=True,
        )

        sample_file = temp_workspace / "Main.kt"
        sample_file.write_text("class Main { fun test() = 42 }\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(temp_workspace), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(temp_workspace), "commit", "-m", "Initial commit"], check=True
        )

        # Snapshot file hashes before analysis
        hashes_before: dict[Path, str] = {}
        for p in temp_workspace.rglob("*"):
            if p.is_file():
                hashes_before[p] = hashlib.sha256(p.read_bytes()).hexdigest()

        # Run all ChangeBlast commands
        main(["doctor", "--repo", str(temp_workspace)])
        main(["profile", "--repo", str(temp_workspace)])
        main(["diff", "--repo", str(temp_workspace)])
        main(["analyze", "--repo", str(temp_workspace)])
        main(["parity", "--repo", str(temp_workspace)])

        # Snapshot file hashes after analysis
        hashes_after: dict[Path, str] = {}
        for p in temp_workspace.rglob("*"):
            if p.is_file():
                hashes_after[p] = hashlib.sha256(p.read_bytes()).hexdigest()

        assert hashes_before == hashes_after, (
            "Workspace files were mutated by ChangeBlast execution!"
        )

        # Verify git status is still clean
        git_status = subprocess.run(
            ["git", "-C", str(temp_workspace), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert git_status.stdout.strip() == "", "Git working tree became dirty during analysis!"

    def test_zero_network_activity(self, temp_workspace: Path) -> None:
        """Verify that ChangeBlast operates completely offline with zero network socket connects."""
        subprocess.run(["git", "-C", str(temp_workspace), "init", "-b", "main"], check=True)
        sample_file = temp_workspace / "App.kt"
        sample_file.write_text("class App\n", encoding="utf-8")

        def forbidden_connect(*args: object, **kwargs: object) -> None:
            raise AssertionError("Unexpected network socket connection attempted by ChangeBlast!")

        with patch.object(socket.socket, "connect", side_effect=forbidden_connect):
            main(["analyze", "--repo", str(temp_workspace), "--format", "json"])
            main(["doctor", "--repo", str(temp_workspace), "--format", "json"])

    def test_no_arbitrary_script_execution(self, temp_workspace: Path) -> None:
        """Verify that repository build scripts are never executed."""
        trap_file = temp_workspace / "TRAP_TRIGGERED.txt"
        gradlew = temp_workspace / "gradlew"
        gradlew.write_text(f"#!/bin/sh\ntouch {trap_file}\n", encoding="utf-8")
        gradlew.chmod(0o755)

        xcodebuild = temp_workspace / "xcodebuild"
        xcodebuild.write_text(f"#!/bin/sh\ntouch {trap_file}\n", encoding="utf-8")
        xcodebuild.chmod(0o755)

        discover_repository(temp_workspace)
        main(["analyze", "--repo", str(temp_workspace)])

        assert not trap_file.exists(), "Repository script was executed during analysis!"
