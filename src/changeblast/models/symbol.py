"""Source code symbol declaration models."""

from __future__ import annotations

from pydantic import Field

from changeblast.models.common import (
    BaseSchemaModel,
    Language,
    SourceLocation,
    SymbolKind,
    Visibility,
)


class SourceSymbol(BaseSchemaModel):
    """Declaration entity in mobile source code (Android Kotlin/Java or iOS Swift)."""

    id: str = Field(
        description="Deterministic URI identifying symbol (e.g. 'kt://com.example.App#login').",
    )
    name: str = Field(description="Short identifier of the symbol.")
    qualified_name: str = Field(description="Fully qualified name within package/module namespace.")
    kind: SymbolKind = Field(description="Syntactic kind of the symbol.")
    language: Language = Field(description="Programming language.")
    visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        description="Access control visibility level.",
    )
    location: SourceLocation = Field(description="Source coordinates in file.")
    container_id: str | None = Field(
        default=None,
        description="ID of parent container symbol (e.g., enclosing class/struct).",
    )
    signature: str | None = Field(
        default=None,
        description="Normalized method signature or property type representation.",
    )
    annotations: list[str] = Field(
        default_factory=list,
        description="Annotations or attributes applied (e.g., '@Composable', '@MainActor').",
    )
    is_entry_point: bool = Field(
        default=False,
        description="True if symbol acts as a UI or app lifecycle entry point.",
    )
    is_test: bool = Field(
        default=False,
        description="True if symbol represents a test class or test method.",
    )
