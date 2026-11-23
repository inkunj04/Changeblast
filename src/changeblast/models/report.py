"""Aggregated change-impact report and risk assessment models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from changeblast.models.changeset import ChangeSet
from changeblast.models.common import BaseSchemaModel, ConfidenceLevel, RiskLevel
from changeblast.models.finding import AnalysisWarning, CrossPlatformCorrelation, ImpactFinding
from changeblast.models.repository import RepositoryProfile


class SummaryMetrics(BaseSchemaModel):
    """Quantitative summary of blast radius calculation."""

    total_files_changed: int = Field(ge=0, description="Total number of modified files.")
    directly_modified_symbols: int = Field(
        ge=0,
        description="Number of symbols directly edited in diffs.",
    )
    direct_impacts_count: int = Field(
        ge=0,
        description="Number of direct callers or subclasses affected (depth 1).",
    )
    transitive_impacts_count: int = Field(
        ge=0,
        description="Number of transitive dependents affected (depth 2+).",
    )
    affected_ui_components_count: int = Field(
        ge=0,
        description="Number of UI screens/views/controllers impacted.",
    )
    suggested_tests_count: int = Field(
        ge=0,
        description="Number of distinct test targets recommended.",
    )
    affected_modules_count: int = Field(
        default=0,
        ge=0,
        description="Number of distinct modules affected.",
    )
    missing_test_coverage_count: int = Field(
        default=0,
        ge=0,
        description="Number of impacted symbols lacking test coverage.",
    )


class RiskAssessment(BaseSchemaModel):
    """Overall deterministic risk score and rationale."""

    level: RiskLevel = Field(description="Categorical risk rating (low, medium, high, critical).")
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.VERIFIED,
        description="Overall confidence rating of the assessment.",
    )
    score: float = Field(
        ge=0.0,
        le=100.0,
        description="Deterministic risk score from 0.0 to 100.0.",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Deterministic factors that contributed to the assigned score.",
    )
    breaking_change_signals: list[str] = Field(
        default_factory=list,
        description="Specific signals indicating potential contract breakage.",
    )


class ImpactReport(BaseSchemaModel):
    """Top-level immutable analysis report produced by ChangeBlast."""

    report_id: str = Field(description="Deterministic hash or UUID for this report run.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="UTC ISO-8601 timestamp of analysis completion.",
    )
    repository: RepositoryProfile = Field(description="Profile of analyzed repository.")
    changeset: ChangeSet = Field(description="Change set under analysis.")
    summary: SummaryMetrics = Field(description="Quantitative metrics overview.")
    overall_risk: RiskAssessment = Field(description="Assessed risk level and breakdown.")
    findings: list[ImpactFinding] = Field(
        default_factory=list,
        description="Detailed impact findings for each affected symbol.",
    )
    warnings: list[AnalysisWarning] = Field(
        default_factory=list,
        description="Non-fatal warnings or diagnostic notices.",
    )
    suggested_tests: list[str] = Field(
        default_factory=list,
        description="Deduplicated list of recommended test targets to run.",
    )
    affected_modules: list[str] = Field(
        default_factory=list,
        description="Distinct modules affected by the changes.",
    )
    missing_test_coverage: list[str] = Field(
        default_factory=list,
        description="Impacted symbols or components lacking test coverage.",
    )
    cross_platform_correlations: list[CrossPlatformCorrelation] = Field(
        default_factory=list,
        description="Evidence-backed correspondences between Android and iOS components.",
    )
    static_analysis_limitations: list[str] = Field(
        default_factory=list,
        description="Explicit disclosures regarding static analysis boundaries.",
    )
