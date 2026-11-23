"""Unit tests for JSON schema versioning and schema export."""

from __future__ import annotations

from changeblast.models import (
    CURRENT_SCHEMA_VERSION,
    ImpactReport,
    SourceSymbol,
    get_schema_for_model,
    is_compatible_version,
)


class TestSchemaVersioning:
    """Validate JSON schema generation and version compatibility rules."""

    def test_current_schema_version_format(self) -> None:
        """Schema version must be a valid SemVer string."""
        parts = CURRENT_SCHEMA_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_schema_compatibility(self) -> None:
        """Major versions must match for compatibility."""
        assert is_compatible_version(CURRENT_SCHEMA_VERSION)
        assert is_compatible_version("1.2.0")
        assert not is_compatible_version("2.0.0")
        assert not is_compatible_version("0.9.0")
        assert not is_compatible_version("invalid-version")

    def test_get_schema_for_model(self) -> None:
        """Verify generated schema conforms to JSON Schema draft-2020-12."""
        schema = get_schema_for_model(ImpactReport)
        assert "$schema" in schema
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["version"] == CURRENT_SCHEMA_VERSION
        assert "properties" in schema
        assert "report_id" in schema["properties"]
        assert "findings" in schema["properties"]

    def test_schema_for_source_symbol(self) -> None:
        """Check schema properties for SourceSymbol."""
        schema = get_schema_for_model(SourceSymbol)
        assert "properties" in schema
        assert "id" in schema["properties"]
        assert "language" in schema["properties"]
        assert "visibility" in schema["properties"]
