"""Version Control System (VCS) adapter port interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from changeblast.models.changeset import ChangeSet
from changeblast.models.repository import RepositoryProfile


class IVcsAdapter(ABC):
    """Abstract interface defining required version control operations."""

    @abstractmethod
    def get_profile(self, repo_path: Path) -> RepositoryProfile:
        """Inspect repository and return a structured RepositoryProfile.

        Args:
            repo_path: Path to root of the repository.

        Returns:
            Discovered RepositoryProfile.

        Raises:
            GitRepositoryNotFoundError: If path is not a valid git repository.
            SecurityBoundaryViolationError: If path escapes filesystem boundaries.
        """
        ...

    @abstractmethod
    def get_changeset(
        self,
        repo_path: Path,
        base_ref: str | None = None,
        target_ref: str | None = None,
    ) -> ChangeSet:
        """Extract modified files and line ranges between references or working tree.

        Args:
            repo_path: Path to root of the repository.
            base_ref: Optional base git reference (e.g. 'main', commit SHA).
            target_ref: Optional target git reference (e.g. 'HEAD', feature branch).

        Returns:
            Extracted ChangeSet model.

        Raises:
            GitReferenceNotFoundError: If a specified git reference does not exist.
            VCSException: On command execution failures.
        """
        ...

    @abstractmethod
    def is_clean(self, repo_path: Path) -> bool:
        """Check whether the working tree is clean with zero uncommitted changes."""
        ...

    @abstractmethod
    def get_file_content(
        self,
        repo_path: Path,
        file_path: str,
        ref: str | None = None,
    ) -> bytes:
        """Retrieve raw file content from disk or a specific git tree ref.

        Args:
            repo_path: Root of the repository.
            file_path: Target relative path from repository root.
            ref: Git commit or ref to read from (None reads from working copy).

        Returns:
            Raw bytes of file content.

        Raises:
            SecurityBoundaryViolationError: If target path escapes repository root.
            FileNotFoundError: If target file does not exist.
        """
        ...
