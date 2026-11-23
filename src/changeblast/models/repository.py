"""Repository profile data models."""

from __future__ import annotations

from pydantic import Field

from changeblast.models.common import BaseSchemaModel, Language, Platform


class VcsMetadata(BaseSchemaModel):
    """Version control context for the analyzed repository."""

    vcs_type: str = Field(default="git", description="VCS system type (e.g. git).")
    branch: str | None = Field(default=None, description="Active branch name if known.")
    commit_sha: str | None = Field(default=None, description="Current commit SHA.")
    is_dirty: bool = Field(
        default=False, description="Whether working tree has uncommitted changes."
    )
    remote_url: str | None = Field(default=None, description="Remote repository URL if available.")


class RepositoryProfile(BaseSchemaModel):
    """Structural profile of an inspected mobile project workspace."""

    root_path: str = Field(description="Normalized path to repository root.")
    platforms: list[Platform] = Field(
        default_factory=list,
        description="Detected mobile platforms (android, ios).",
    )
    languages: list[Language] = Field(
        default_factory=list,
        description="Detected programming languages in source files.",
    )
    source_roots: list[str] = Field(
        default_factory=list,
        description="Relative directories containing production source code.",
    )
    test_roots: list[str] = Field(
        default_factory=list,
        description="Relative directories containing test source code.",
    )
    build_files: list[str] = Field(
        default_factory=list,
        description="Detected project build files (build.gradle.kts, Package.swift, etc.).",
    )
    vcs: VcsMetadata | None = Field(
        default=None,
        description="VCS metadata if repository is under version control.",
    )
