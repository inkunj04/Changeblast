"""Safe, read-only Git operations adapter implementing IVcsAdapter."""

from __future__ import annotations

import contextlib
import re
import subprocess
from pathlib import Path

from changeblast.discovery.scanner import discover_repository, is_path_excluded
from changeblast.exceptions import (
    GitReferenceNotFoundError,
    GitRepositoryNotFoundError,
    SecurityBoundaryViolationError,
    VCSException,
)
from changeblast.models.changeset import ChangedFile, ChangeSet, DiffHunk
from changeblast.models.common import ChangeType, LineRange
from changeblast.models.repository import RepositoryProfile, VcsMetadata
from changeblast.ports.vcs import IVcsAdapter

# Regex for parsing git diff hunk headers: @@ -10,5 +12,8 @@ optional context
HUNK_HEADER_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(?:[ ]?(.*))?")


def validate_path_within_root(repo_root: Path, file_path: str | Path) -> Path:
    """Ensure target path resolves strictly below repository root."""
    if isinstance(file_path, str) and "\0" in file_path:
        raise SecurityBoundaryViolationError("Null byte injection detected in path.")
    try:
        resolved_root = repo_root.resolve()
        target = (resolved_root / file_path).resolve()
    except (ValueError, TypeError) as exc:
        raise SecurityBoundaryViolationError(f"Invalid path representation: {exc}") from exc

    if not target.is_relative_to(resolved_root):
        raise SecurityBoundaryViolationError(
            f"Path traversal detected: '{file_path}' escapes repository root '{resolved_root}'."
        )
    return target


class GitAdapter(IVcsAdapter):
    """Production-grade read-only Git adapter.

    Guarantees zero repository state modifications (never executes write operations).
    """

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path.resolve()
        self._verify_git_repository()

    def _verify_git_repository(self) -> None:
        """Verify that repo_path is inside a valid git working tree."""
        if not self.repo_path.exists() or not self.repo_path.is_dir():
            raise GitRepositoryNotFoundError(f"Directory does not exist: {self.repo_path}")

        try:
            res = self._run_git(["rev-parse", "--is-inside-work-tree"])
            if res.strip() != "true":
                raise GitRepositoryNotFoundError(f"Not a git working tree: {self.repo_path}")
        except VCSException as exc:
            raise GitRepositoryNotFoundError(f"Not a git repository: {self.repo_path}") from exc

    def _run_git(self, args: list[str]) -> str:
        """Execute a read-only git subcommand via explicit argument array (no shell=True)."""
        cmd = ["git", "-C", str(self.repo_path), *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise VCSException("Git executable not found in system PATH.") from exc

        if proc.returncode != 0:
            err_msg = proc.stderr.strip()
            if "fatal: Not a valid object name" in err_msg or "unknown revision" in err_msg:
                raise GitReferenceNotFoundError(f"Git ref not found: {err_msg}")
            raise VCSException(f"Git command failed ({' '.join(args)}): {err_msg}")

        return proc.stdout

    def is_clean(self, repo_path: Path | None = None) -> bool:
        """Return True if working tree has no uncommitted changes."""
        output = self._run_git(["status", "--porcelain=v1"])
        return len(output.strip()) == 0

    def get_profile(self, repo_path: Path | None = None) -> RepositoryProfile:
        """Discover mobile structure and attach VCS metadata."""
        target = (repo_path or self.repo_path).resolve()
        profile = discover_repository(target)

        # Enhance with live git details
        branch: str | None = None
        commit_sha: str | None = None
        with contextlib.suppress(Exception):
            branch_out = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
            if branch_out and branch_out != "HEAD":
                branch = branch_out

        with contextlib.suppress(Exception):
            commit_sha = self._run_git(["rev-parse", "HEAD"]).strip()

        is_dirty = not self.is_clean()

        vcs_meta = VcsMetadata(
            vcs_type="git",
            branch=branch,
            commit_sha=commit_sha,
            is_dirty=is_dirty,
        )

        # Return updated profile with live git metadata
        return profile.model_copy(update={"vcs": vcs_meta})

    def get_changeset(
        self,
        repo_path: Path | None = None,
        base_ref: str | None = None,
        target_ref: str | None = None,
    ) -> ChangeSet:
        """Extract diff between commits, branches, or against the active working tree."""
        is_working_tree = target_ref is None

        diff_args = ["diff", "--unified=0", "--no-color", "--no-ext-diff"]
        if base_ref and target_ref:
            # Commit or branch comparison: base_ref...target_ref
            diff_args.append(f"{base_ref}...{target_ref}")
        elif base_ref and not target_ref:
            # Compared to working tree: git diff base_ref
            diff_args.append(base_ref)
        else:
            # Default uncommitted working tree changes: git diff HEAD (includes staged and unstaged)
            try:
                self._run_git(["rev-parse", "HEAD"])
                diff_args.append("HEAD")
            except VCSException:
                # Initial commit with no HEAD yet
                diff_args = ["diff", "--unified=0", "--no-color", "--no-ext-diff", "--cached"]

        diff_output = self._run_git(diff_args)
        changed_files = self._parse_diff_output(diff_output)

        # If analyzing working tree, also include untracked newly added files
        if is_working_tree:
            untracked = self._get_untracked_files()
            for ufile in untracked:
                if not any(cf.path == ufile for cf in changed_files):
                    file_path = self.repo_path / ufile
                    line_count = 0
                    if file_path.is_file():
                        try:
                            line_count = len(file_path.read_bytes().splitlines())
                        except Exception:
                            line_count = 1
                    changed_files.append(
                        ChangedFile(
                            path=ufile,
                            change_type=ChangeType.ADDED,
                            changed_line_ranges=[
                                LineRange(start_line=1, end_line=max(1, line_count))
                            ],
                            hunks=[
                                DiffHunk(
                                    old_start=0, old_length=0, new_start=1, new_length=line_count
                                )
                            ],
                        )
                    )

        # Compute total additions and deletions
        total_adds = sum(sum(h.new_length for h in cf.hunks) for cf in changed_files)
        total_dels = sum(sum(h.old_length for h in cf.hunks) for cf in changed_files)

        return ChangeSet(
            base_ref=base_ref,
            target_ref=target_ref,
            is_working_tree=is_working_tree,
            changed_files=changed_files,
            total_additions=total_adds,
            total_deletions=total_dels,
        )

    def _get_untracked_files(self) -> list[str]:
        """Find untracked files in working tree, excluding build caches."""
        status_out = self._run_git(["status", "--porcelain=v1", "-uall"])
        untracked: list[str] = []
        for line in status_out.splitlines():
            if line.startswith("?? "):
                rel_path = line[3:].strip().strip('"')
                if not is_path_excluded(Path(rel_path)):
                    untracked.append(rel_path.replace("\\", "/"))
        return untracked

    def _parse_diff_output(self, diff_text: str) -> list[ChangedFile]:
        """Parse unified diff output into structured ChangedFile models."""
        files: list[ChangedFile] = []
        raw_file_diffs = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)

        for chunk in raw_file_diffs:
            chunk = chunk.strip()
            if not chunk or not chunk.startswith("diff --git"):
                continue

            lines = chunk.splitlines()
            header_line = lines[0]
            # diff --git a/path b/path
            paths_match = re.match(r"^diff --git a/(.*) b/(.*)$", header_line)
            if not paths_match:
                continue

            old_path = paths_match.group(1)
            new_path = paths_match.group(2)

            change_type = ChangeType.MODIFIED
            target_path = new_path
            old_recorded_path: str | None = None

            for line in lines[1:10]:
                if line.startswith("new file mode"):
                    change_type = ChangeType.ADDED
                elif line.startswith("deleted file mode"):
                    change_type = ChangeType.DELETED
                    target_path = old_path
                elif line.startswith("rename from "):
                    change_type = ChangeType.RENAMED
                    old_recorded_path = line.replace("rename from ", "").strip()
                elif line.startswith("rename to "):
                    target_path = line.replace("rename to ", "").strip()

            # Ignore excluded directories
            if is_path_excluded(Path(target_path)):
                continue

            # Parse hunks and affected line ranges
            hunks: list[DiffHunk] = []
            changed_ranges: list[LineRange] = []

            for line in lines:
                if line.startswith("@@"):
                    m = HUNK_HEADER_RE.match(line)
                    if m:
                        old_start = int(m.group(1))
                        old_len = int(m.group(2)) if m.group(2) is not None else 1
                        new_start = int(m.group(3))
                        new_len = int(m.group(4)) if m.group(4) is not None else 1
                        header_ctx = m.group(5)

                        hunk = DiffHunk(
                            old_start=old_start,
                            old_length=old_len,
                            new_start=new_start,
                            new_length=new_len,
                            header=header_ctx.strip() if header_ctx else None,
                        )
                        hunks.append(hunk)

                        # Record changed line range in new version if line count > 0
                        if new_len > 0:
                            start_l = new_start
                            end_l = new_start + new_len - 1
                            changed_ranges.append(LineRange(start_line=start_l, end_line=end_l))
                        elif new_len == 0 and change_type == ChangeType.MODIFIED:
                            # Pure deletion at line: map coordinate to surrounding line
                            changed_ranges.append(
                                LineRange(start_line=max(1, new_start), end_line=max(1, new_start))
                            )

            files.append(
                ChangedFile(
                    path=target_path.replace("\\", "/"),
                    change_type=change_type,
                    old_path=old_recorded_path.replace("\\", "/") if old_recorded_path else None,
                    changed_line_ranges=changed_ranges,
                    hunks=hunks,
                )
            )

        return files

    def get_file_content(
        self,
        repo_path: Path | None = None,
        file_path: str = "",
        ref: str | None = None,
    ) -> bytes:
        """Safely read file content from working tree or specific git revision."""
        root = (repo_path or self.repo_path).resolve()
        validated_file = validate_path_within_root(root, file_path)

        if ref is None:
            # Read directly from working copy
            if not validated_file.exists() or not validated_file.is_file():
                raise FileNotFoundError(f"File not found: {validated_file}")
            return validated_file.read_bytes()
        else:
            # Read from git object database: git show <ref>:<rel_path>
            rel = str(validated_file.relative_to(root)).replace("\\", "/")
            try:
                proc = subprocess.run(
                    ["git", "-C", str(root), "show", f"{ref}:{rel}"],
                    capture_output=True,
                    check=False,
                )
                if proc.returncode != 0:
                    raise FileNotFoundError(f"File '{rel}' not found at revision '{ref}'")
                return proc.stdout
            except FileNotFoundError as exc:
                raise VCSException("Git executable not found.") from exc
