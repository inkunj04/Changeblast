"""Dependency and call graph edge models."""

from __future__ import annotations

from pydantic import Field

from changeblast.models.common import (
    BaseSchemaModel,
    ConfidenceLevel,
    EdgeKind,
    SourceLocation,
)
from changeblast.models.evidence import EvidenceReference


class DependencyEdge(BaseSchemaModel):
    """Directed dependency or invocation relationship between two symbols."""

    source_symbol_id: str = Field(description="ID of originating symbol (e.g. caller or subclass).")
    target_symbol_id: str = Field(description="ID of target symbol being depended on or invoked.")
    edge_kind: EdgeKind = Field(description="Nature of the dependency relationship.")
    location: SourceLocation | None = Field(
        default=None,
        description="Location in source code where the invocation or reference occurs.",
    )
    is_dynamic: bool = Field(
        default=False,
        description="True if invocation uses dynamic dispatch, reflection, or late binding.",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Traversable edge weight for graph prioritization.",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.VERIFIED,
        description="Confidence level of this relationship.",
    )
    evidence: list[EvidenceReference] = Field(
        default_factory=list,
        description="Verifiable evidence references validating this edge.",
    )
