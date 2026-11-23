"""Unit tests for GitAdapter, diff parsing, and read-only changeset analysis."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from changeblast.adapters.git import GitAdapter, validate_path_within_root
from changeblast.exceptions import GitReferenceNotFoundError, SecurityBoundaryViolationError
from changeblast.models.common import ChangeType


def run_git(repo: Path, *args: str) -> str:
    """Helper to run git commands to construct synthetic git history for testing."""
    cmd = ["git", "-C", str(repo), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


@pytest.fixture
def initialized_git_repo(temp_workspace: Path) -> Path:
    """Fixture initializing a clean git repository with initial commit."""
    run_git(temp_workspace, "init", "-b", "main")
    run_git(temp_workspace, "config", "user.name", "Test User")
    run_git(temp_workspace, "config", "user.email", "test@example.com")

    # Initial file
    init_file = temp_workspace / "README.md"
    init_file.write_text("# Project\nInitial line 1\nInitial line 2\n", encoding="utf-8")
    run_git(temp_workspace, "add", "README.md")
    run_git(temp_workspace, "commit", "-m", "Initial commit")
    return temp_workspace


class TestGitAdapter:
    """Verify git changeset extraction, diff line mapping, and security boundaries."""

    def test_clean_status(self, initialized_git_repo: Path) -> None:
        adapter = GitAdapter(initialized_git_repo)
        assert adapter.is_clean() is True

        # Introduce uncommitted change
        (initialized_git_repo / "README.md").write_text("Modified content\n", encoding="utf-8")
        assert adapter.is_clean() is False

    def test_working_tree_changeset_and_line_ranges(self, initialized_git_repo: Path) -> None:
        adapter = GitAdapter(initialized_git_repo)

        # Modify existing file
        (initialized_git_repo / "README.md").write_text(
            "# Project\nModified line 1\nNew line inserted\nInitial line 2\n", encoding="utf-8"
        )
        # Create untracked new file
        (initialized_git_repo / "NewFile.kt").write_text("class NewFile\n", encoding="utf-8")

        changeset = adapter.get_changeset()
        assert changeset.is_working_tree is True
        assert len(changeset.changed_files) == 2

        file_map = {cf.path: cf for cf in changeset.changed_files}
        assert "README.md" in file_map
        assert "NewFile.kt" in file_map

        readme_diff = file_map["README.md"]
        assert readme_diff.change_type == ChangeType.MODIFIED
        assert len(readme_diff.changed_line_ranges) >= 1

        new_file_diff = file_map["NewFile.kt"]
        assert new_file_diff.change_type == ChangeType.ADDED
        assert new_file_diff.changed_line_ranges[0].start_line == 1

    def test_commit_and_branch_comparison(self, initialized_git_repo: Path) -> None:
        adapter = GitAdapter(initialized_git_repo)
        c1 = run_git(initialized_git_repo, "rev-parse", "HEAD")

        # Create branch and commit changes
        run_git(initialized_git_repo, "checkout", "-b", "feature/auth")
        auth_file = initialized_git_repo / "Auth.kt"
        auth_file.write_text("class Auth {\n    fun login() {}\n}\n", encoding="utf-8")
        run_git(initialized_git_repo, "add", "Auth.kt")
        run_git(initialized_git_repo, "commit", "-m", "Add auth")
        c2 = run_git(initialized_git_repo, "rev-parse", "HEAD")

        # Compare commits
        changeset = adapter.get_changeset(base_ref=c1, target_ref=c2)
        assert changeset.is_working_tree is False
        assert len(changeset.changed_files) == 1
        assert changeset.changed_files[0].path == "Auth.kt"
        assert changeset.changed_files[0].change_type == ChangeType.ADDED

        # Compare branches
        branch_changeset = adapter.get_changeset(base_ref="main", target_ref="feature/auth")
        assert len(branch_changeset.changed_files) == 1

    def test_deleted_and_renamed_files(self, initialized_git_repo: Path) -> None:
        adapter = GitAdapter(initialized_git_repo)

        # Commit an initial source file
        src_file = initialized_git_repo / "OldName.kt"
        src_file.write_text("class RenamedMe\n", encoding="utf-8")
        run_git(initialized_git_repo, "add", "OldName.kt")
        run_git(initialized_git_repo, "commit", "-m", "Add OldName")

        # Rename file using git mv
        run_git(initialized_git_repo, "mv", "OldName.kt", "NewName.kt")
        changeset = adapter.get_changeset()
        renamed = [cf for cf in changeset.changed_files if cf.path == "NewName.kt"][0]
        assert renamed.change_type == ChangeType.RENAMED
        assert renamed.old_path == "OldName.kt"

        # Commit rename and then delete
        run_git(initialized_git_repo, "commit", "-m", "Rename")
        run_git(initialized_git_repo, "rm", "NewName.kt")
        del_changeset = adapter.get_changeset()
        deleted = [cf for cf in del_changeset.changed_files if cf.path == "NewName.kt"][0]
        assert deleted.change_type == ChangeType.DELETED

    def test_safe_get_file_content(self, initialized_git_repo: Path) -> None:
        adapter = GitAdapter(initialized_git_repo)

        # Working tree read
        content = adapter.get_file_content(file_path="README.md")
        assert b"# Project" in content

        # Git ref read
        head_content = adapter.get_file_content(file_path="README.md", ref="HEAD")
        assert b"# Project" in head_content

    def test_path_traversal_protection(self, initialized_git_repo: Path) -> None:
        adapter = GitAdapter(initialized_git_repo)
        with pytest.raises(SecurityBoundaryViolationError):
            validate_path_within_root(initialized_git_repo, "../../../etc/passwd")

        with pytest.raises(SecurityBoundaryViolationError):
            adapter.get_file_content(file_path="../../outside.txt")

    def test_invalid_git_ref_raises_error(self, initialized_git_repo: Path) -> None:
        adapter = GitAdapter(initialized_git_repo)
        with pytest.raises(GitReferenceNotFoundError):
            adapter.get_changeset(base_ref="non_existent_branch_xyz")
