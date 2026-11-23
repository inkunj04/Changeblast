"""Evidence and verification reference models."""

from __future__ import annotations

from pydantic import Field

from changeblast.models.common import BaseSchemaModel, EvidenceType, SourceLocation


class EvidenceReference(BaseSchemaModel):
    """Verifiable proof and context explaining an impact finding."""

    evidence_type: EvidenceType = Field(
        description="Category of the evidence (e.g. call_site, inheritance_chain).",
    )
    location: SourceLocation = Field(
        description="Exact file and line where the proof was observed."
    )
    description: str = Field(description="Human-readable explanation of why this link exists.")
    snippet: str | None = Field(
        default=None,
        description="Optional sanitized code snippet demonstrating the call site or declaration.",
    )
