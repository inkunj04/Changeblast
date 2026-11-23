"""Impact findings and analysis warnings models."""

from __future__ import annotations

from pydantic import Field

from changeblast.models.common import (
    BaseSchemaModel,
    ConfidenceLevel,
    MobileDomain,
    Platform,
    RiskLevel,
    WarningCategory,
)
from changeblast.models.evidence import EvidenceReference
from changeblast.models.symbol import SourceSymbol


class CrossPlatformCorrelation(BaseSchemaModel):
    """Evidence-backed relationship between corresponding Android and iOS components."""

    feature_name: str = Field(description="Name of the correlated feature or domain.")
    android_symbol_id: str = Field(description="Associated Android symbol ID.")
    ios_symbol_id: str = Field(description="Associated iOS symbol ID.")
    correlation_type: str = Field(
        description="Basis of correlation: 'api_contract', 'feature_mapping', 'screen_flow', 'shared_behavior'."
    )
    evidence: list[EvidenceReference] = Field(
        default_factory=list,
        description="Verifiable evidence linking components across platforms.",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.STRONG_INFERENCE,
        description="Confidence rating of the cross-platform correspondence.",
    )
    notes: str = Field(
        description="Observations and explicit behavioral divergence disclosure.",
    )


class AnalysisWarning(BaseSchemaModel):
    """Non-fatal diagnostic condition or heuristic edge case encountered."""

    warning_id: str = Field(description="Unique deterministic ID for this warning.")
    category: WarningCategory = Field(description="Classification of the warning.")
    message: str = Field(description="Explanatory message describing the warning.")
    file_path: str | None = Field(default=None, description="Related file path if applicable.")
    line_number: int | None = Field(
        default=None,
        ge=1,
        description="Related line number if applicable.",
    )
    remediation: str | None = Field(
        default=None,
        description="Suggested action for developer or CI pipeline.",
    )


class ImpactFinding(BaseSchemaModel):
    """Detailed observation of an impacted symbol within the blast radius."""

    finding_id: str = Field(description="Unique deterministic identifier for this finding.")
    target_symbol: SourceSymbol = Field(description="The symbol affected by the change.")
    root_changed_symbol_id: str = Field(
        description="The directly modified symbol that initiated propagation.",
    )
    depth: int = Field(
        ge=0,
        description="Propagation distance (0=directly modified, 1=direct dependent, 2+=transitive).",
    )
    propagation_path: list[str] = Field(
        default_factory=list,
        description="Chain of symbol IDs linking the root change to the target symbol.",
    )
    evidence: list[EvidenceReference] = Field(
        default_factory=list,
        description="List of verifiable evidence references validating the impact.",
    )
    is_breaking: bool = Field(
        default=False,
        description="True if finding indicates probable binary or source breaking change.",
    )
    is_ui_affected: bool = Field(
        default=False,
        description="True if this finding reaches a UI component or user-facing screen.",
    )
    suggested_tests: list[str] = Field(
        default_factory=list,
        description="List of test symbol IDs or test file paths recommended for verification.",
    )
    severity: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Assessed severity level of the impact on this component.",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.VERIFIED,
        description="Assessed confidence level of this impact finding.",
    )
    affected_modules: list[str] = Field(
        default_factory=list,
        description="Modules containing this impacted component.",
    )
    related_features: list[str] = Field(
        default_factory=list,
        description="Identified feature domains related to this finding.",
    )
    platform: Platform = Field(
        default=Platform.ANDROID,
        description="Mobile platform for this finding (android, ios, cross_platform).",
    )
    mobile_domain: MobileDomain = Field(
        default=MobileDomain.GENERAL,
        description="Mobile architectural subdomain involved.",
    )
    potential_consequence: str | None = Field(
        default=None,
        description="Concrete runtime failure mode or production consequence if broken.",
    )
