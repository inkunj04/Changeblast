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


class GradleModule(BaseSchemaModel):
    """Discovered Gradle module in an Android or multi-project repository."""

    name: str = Field(description="Gradle module identifier (e.g. ':app', ':core:data').")
    path: str = Field(description="Relative path from repository root to module folder.")
    build_file: str = Field(description="Relative path to module build script.")
    source_roots: list[str] = Field(
        default_factory=list, description="Discovered source directories."
    )
    test_roots: list[str] = Field(default_factory=list, description="Discovered test directories.")


class XcodeTarget(BaseSchemaModel):
    """Discovered target inside an Xcode project or workspace."""

    name: str = Field(description="Target identifier.")
    target_type: str = Field(
        default="application",
        description="Target type (e.g., application, framework, unit_test, ui_test).",
    )
    source_roots: list[str] = Field(
        default_factory=list, description="Discovered source directories for target."
    )
    test_roots: list[str] = Field(
        default_factory=list, description="Discovered test directories for target."
    )


class XcodeProject(BaseSchemaModel):
    """Discovered Xcode project or workspace."""

    name: str = Field(description="Project or workspace name.")
    path: str = Field(description="Relative path to .xcodeproj or .xcworkspace.")
    is_workspace: bool = Field(default=False, description="True if path is an .xcworkspace.")
    targets: list[XcodeTarget] = Field(
        default_factory=list, description="Discovered targets in this project."
    )


class SwiftPackage(BaseSchemaModel):
    """Discovered Swift package in an iOS or multi-platform project."""

    name: str = Field(description="Package name.")
    path: str = Field(description="Relative path to package directory.")
    manifest_path: str = Field(
        default="Package.swift", description="Relative path to Package.swift."
    )
    targets: list[str] = Field(default_factory=list, description="Declared package target names.")


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
    is_monorepo: bool = Field(
        default=False,
        description="True if repository contains multiple mobile apps or sub-projects.",
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
    gradle_modules: list[GradleModule] = Field(
        default_factory=list,
        description="Discovered Gradle modules for Android.",
    )
    xcode_projects: list[XcodeProject] = Field(
        default_factory=list,
        description="Discovered Xcode projects and workspaces.",
    )
    swift_packages: list[SwiftPackage] = Field(
        default_factory=list,
        description="Discovered Swift Package Manager packages.",
    )
    vcs: VcsMetadata | None = Field(
        default=None,
        description="VCS metadata if repository is under version control.",
    )
