"""Common enumerations, base models, and schema versioning for ChangeBlast."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

CURRENT_SCHEMA_VERSION = "1.0.0"


class Platform(StrEnum):
    """Target mobile platforms."""

    ANDROID = "android"
    IOS = "ios"


class Language(StrEnum):
    """Supported mobile programming languages."""

    KOTLIN = "kotlin"
    JAVA = "java"
    SWIFT = "swift"


class SymbolKind(StrEnum):
    """Syntactic categories of code declarations."""

    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    VARIABLE = "variable"
    ANNOTATION = "annotation"


class Visibility(StrEnum):
    """Access control visibility levels."""

    PUBLIC = "public"
    PROTECTED = "protected"
    INTERNAL = "internal"
    PRIVATE = "private"
    PACKAGE_PRIVATE = "package_private"


class ChangeType(StrEnum):
    """Type of modification recorded in version control diffs."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class EdgeKind(StrEnum):
    """Relationship categories between symbols in dependency and call graphs."""

    CALLS = "calls"
    OVERRIDES = "overrides"
    IMPLEMENTS = "implements"
    EXTENDS = "extends"
    REFERENCES = "references"
    INSTANTIATES = "instantiates"
    IMPORTS = "imports"


class EvidenceType(StrEnum):
    """Classification of verifiable proof linking changed symbols to findings."""

    DIRECT_DIFF_MATCH = "direct_diff_match"
    CALL_SITE = "call_site"
    INHERITANCE_CHAIN = "inheritance_chain"
    TYPE_REFERENCE = "type_reference"
    IMPORT_STATEMENT = "import_statement"
    UI_NAVIGATION = "ui_navigation"
    TEST_ASSERTION = "test_assertion"


class RiskLevel(StrEnum):
    """Categorical risk assessment for impact blast radius."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(StrEnum):
    """Confidence classification for relationships and impact findings."""

    VERIFIED = "verified"
    STRONG_INFERENCE = "strong_inference"
    POSSIBLE = "possible"
    UNKNOWN = "unknown"


class WarningCategory(StrEnum):
    """Non-fatal condition categories encountered during analysis."""

    SYNTAX_ERROR_RECOVERY = "syntax_error_recovery"
    UNRESOLVED_SYMBOL = "unresolved_symbol"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    AMBIGUOUS_CALL = "ambiguous_call"
    FILE_READ_ERROR = "file_read_error"
    MAX_DEPTH_EXCEEDED = "max_depth_exceeded"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    MISSING_TEST_COVERAGE = "missing_test_coverage"
    DELETED_SYMBOL_WITH_DEPENDENTS = "deleted_symbol_with_dependents"


class BaseSchemaModel(BaseModel):
    """Base class for all ChangeBlast domain models with schema versioning.

    Configured to be frozen (immutable) for thread-safety and hashing.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
        use_enum_values=True,
    )

    schema_version: str = Field(
        default=CURRENT_SCHEMA_VERSION,
        description="Semantic version string of the data contract schema.",
    )


class SourceLocation(BaseSchemaModel):
    """Exact source coordinates within a file."""

    file_path: str = Field(description="Relative path of file from workspace root.")
    start_line: int = Field(ge=1, description="1-based starting line number.")
    start_column: int = Field(ge=0, description="0-based starting column.")
    end_line: int = Field(ge=1, description="1-based ending line number.")
    end_column: int = Field(ge=0, description="0-based ending column.")


class LineRange(BaseSchemaModel):
    """Inclusive line range representing changed lines in diffs."""

    start_line: int = Field(ge=1, description="1-based start line.")
    end_line: int = Field(ge=1, description="1-based end line.")

    def contains(self, line: int) -> bool:
        """Check whether a line number falls within this range."""
        return self.start_line <= line <= self.end_line

    def overlaps(self, other: LineRange) -> bool:
        """Check whether this range overlaps with another line range."""
        return self.start_line <= other.end_line and self.end_line >= other.start_line


def is_compatible_version(version: str) -> bool:
    """Check if the provided schema version is compatible with current schema version.

    Follows SemVer major compatibility: major versions must match.
    """
    try:
        major_curr = CURRENT_SCHEMA_VERSION.split(".")[0]
        major_in = version.split(".")[0]
        return major_curr == major_in
    except Exception:
        return False


def get_schema_for_model(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Export the standard JSON Schema definition for any ChangeBlast model."""
    schema = model_cls.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["version"] = CURRENT_SCHEMA_VERSION
    return schema
