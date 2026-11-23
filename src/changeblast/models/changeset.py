"""ChangeSet and diff data models."""

from __future__ import annotations

from pydantic import Field

from changeblast.models.common import BaseSchemaModel, ChangeType, LineRange


class DiffHunk(BaseSchemaModel):
    """Individual modification hunk from unified diff."""

    old_start: int = Field(ge=0, description="Start line in old file.")
    old_length: int = Field(ge=0, description="Line count in old file.")
    new_start: int = Field(ge=0, description="Start line in new file.")
    new_length: int = Field(ge=0, description="Line count in new file.")
    header: str | None = Field(default=None, description="Context header text.")


class ChangedFile(BaseSchemaModel):
    """Represents a single file altered in the changeset."""

    path: str = Field(description="Target file path relative to repo root.")
    change_type: ChangeType = Field(
        description="Nature of the change (added, modified, deleted, renamed)."
    )
    old_path: str | None = Field(default=None, description="Previous file path if renamed.")
    changed_line_ranges: list[LineRange] = Field(
        default_factory=list,
        description="Affected line ranges in the current/new file version.",
    )
    hunks: list[DiffHunk] = Field(
        default_factory=list,
        description="Parsed diff hunks for detailed inspection.",
    )


class ChangeSet(BaseSchemaModel):
    """Aggregated collection of file modifications under analysis."""

    base_ref: str | None = Field(default=None, description="Base commit, branch, or ref.")
    target_ref: str | None = Field(default=None, description="Target commit, branch, or ref.")
    is_working_tree: bool = Field(
        default=False,
        description="True if analysis includes dirty/uncommitted working tree changes.",
    )
    changed_files: list[ChangedFile] = Field(
        default_factory=list,
        description="List of files modified in this change set.",
    )
    total_additions: int = Field(ge=0, default=0, description="Total added lines across files.")
    total_deletions: int = Field(ge=0, default=0, description="Total deleted lines across files.")
