"""Unit tests for ChangeBlast typed data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from changeblast.models import (
    CURRENT_SCHEMA_VERSION,
    ImpactReport,
    LineRange,
    RiskAssessment,
    RiskLevel,
    SourceLocation,
    SourceSymbol,
)


class TestDataModels:
    """Validate model instantiation, validation constraints, and immutability."""

    def test_source_location_creation_and_bounds(self) -> None:
        loc = SourceLocation(
            file_path="src/Main.kt",
            start_line=1,
            start_column=0,
            end_line=10,
            end_column=20,
        )
        assert loc.file_path == "src/Main.kt"
        assert loc.start_line == 1
        assert loc.end_line == 10
        assert loc.schema_version == CURRENT_SCHEMA_VERSION

        # Test invalid line bounds (< 1 must fail)
        with pytest.raises(ValidationError):
            SourceLocation(
                file_path="src/Main.kt",
                start_line=0,
                start_column=0,
                end_line=1,
                end_column=1,
            )

    def test_line_range_contains_and_overlaps(self) -> None:
        lr = LineRange(start_line=10, end_line=20)
        assert lr.contains(10)
        assert lr.contains(15)
        assert lr.contains(20)
        assert not lr.contains(9)
        assert not lr.contains(21)

        overlapping = LineRange(start_line=18, end_line=25)
        assert lr.overlaps(overlapping)
        assert overlapping.overlaps(lr)

        disjoint = LineRange(start_line=25, end_line=30)
        assert not lr.overlaps(disjoint)

    def test_model_immutability(self, sample_symbol: SourceSymbol) -> None:
        """Models must be frozen and reject attribute mutation."""
        with pytest.raises(ValidationError):
            sample_symbol.name = "new_name"

    def test_extra_fields_forbidden(self) -> None:
        """Models must forbid undeclared extra fields."""
        with pytest.raises(ValidationError):
            SourceLocation(
                file_path="src/Main.kt",
                start_line=1,
                start_column=0,
                end_line=5,
                end_column=10,
                unexpected_field="disallowed",  # type: ignore[call-arg]
            )

    def test_risk_assessment_score_bounds(self) -> None:
        """Risk score must remain strictly between 0.0 and 100.0."""
        valid_risk = RiskAssessment(
            level=RiskLevel.MEDIUM,
            score=50.0,
            reasons=["Transitive caller impacted"],
        )
        assert valid_risk.score == 50.0

        with pytest.raises(ValidationError):
            RiskAssessment(level=RiskLevel.LOW, score=-0.1)

        with pytest.raises(ValidationError):
            RiskAssessment(level=RiskLevel.CRITICAL, score=100.1)

    def test_impact_report_serialization_roundtrip(self, sample_report: ImpactReport) -> None:
        """Validate serialization to JSON and clean round-trip reconstitution."""
        json_str = sample_report.model_dump_json()
        assert "report-20261123-001" in json_str
        assert "kt://com.example.auth.AuthManager#authenticate" in json_str

        # Roundtrip back from JSON
        reconstituted = ImpactReport.model_validate_json(json_str)
        assert reconstituted.report_id == sample_report.report_id
        assert reconstituted.overall_risk.level == sample_report.overall_risk.level
        assert reconstituted.overall_risk.score == sample_report.overall_risk.score
        assert len(reconstituted.findings) == len(sample_report.findings)
        assert reconstituted.findings[0].depth == sample_report.findings[0].depth
        assert reconstituted.schema_version == CURRENT_SCHEMA_VERSION
