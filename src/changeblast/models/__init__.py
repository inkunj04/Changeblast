"""ChangeBlast typed data models with JSON schema versioning."""

from changeblast.models.changeset import ChangedFile, ChangeSet, DiffHunk
from changeblast.models.common import (
    CURRENT_SCHEMA_VERSION,
    BaseSchemaModel,
    ChangeType,
    EdgeKind,
    EvidenceType,
    Language,
    LineRange,
    Platform,
    RiskLevel,
    SourceLocation,
    SymbolKind,
    Visibility,
    WarningCategory,
    get_schema_for_model,
    is_compatible_version,
)
from changeblast.models.edge import DependencyEdge
from changeblast.models.evidence import EvidenceReference
from changeblast.models.finding import AnalysisWarning, ImpactFinding
from changeblast.models.report import ImpactReport, RiskAssessment, SummaryMetrics
from changeblast.models.repository import RepositoryProfile, VcsMetadata
from changeblast.models.symbol import SourceSymbol

__all__ = [
    "AnalysisWarning",
    "BaseSchemaModel",
    "CURRENT_SCHEMA_VERSION",
    "ChangeSet",
    "ChangeType",
    "ChangedFile",
    "DependencyEdge",
    "DiffHunk",
    "EdgeKind",
    "EvidenceReference",
    "EvidenceType",
    "ImpactFinding",
    "ImpactReport",
    "Language",
    "LineRange",
    "Platform",
    "RepositoryProfile",
    "RiskAssessment",
    "RiskLevel",
    "SourceLocation",
    "SourceSymbol",
    "SummaryMetrics",
    "SymbolKind",
    "VcsMetadata",
    "Visibility",
    "WarningCategory",
    "get_schema_for_model",
    "is_compatible_version",
]
