"""Canonical knowledge records and provenance models for Eden."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from eden.knowledge.types import (
    ConfidenceLevel,
    KnowledgeType,
    SourceType,
    VerificationStatus,
)


def utc_now() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Provenance:
    """Traceable information about where knowledge came from."""

    source_type: SourceType
    source_id: str
    timestamp: str = field(default_factory=utc_now)
    tool: str | None = None
    operation: str | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("Provenance source_id cannot be empty.")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Provenance confidence must be between 0 and 1.")


@dataclass(frozen=True)
class Evidence:
    """A traceable item that may support or challenge a knowledge claim."""

    id: str
    source: Provenance
    excerpt: str
    supports_claim: bool | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Evidence ID cannot be empty.")
        if not self.excerpt.strip():
            raise ValueError("Evidence excerpt cannot be empty.")


@dataclass
class KnowledgeRecord:
    """Canonical logical representation of a unit of knowledge.

    This model is independent of the database representation. Persistence,
    relationships, and revision history will be implemented in their own
    layers and connected to this contract.
    """

    content: str
    knowledge_type: KnowledgeType
    provenance: list[Provenance]

    id: str = field(default_factory=lambda: str(uuid4()))
    confidence: float | None = None
    confidence_level: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    verification: VerificationStatus = VerificationStatus.UNVERIFIED
    importance: int = 3
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    relevant_from: str | None = None
    relevant_until: str | None = None
    revision: int = 1
    evidence_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Knowledge record ID cannot be empty.")
        if not self.content.strip():
            raise ValueError("Knowledge content cannot be empty.")
        if not isinstance(self.knowledge_type, KnowledgeType):
            raise TypeError("knowledge_type must be a KnowledgeType.")
        if self.confidence is not None:
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("Confidence must be between 0 and 1.")
        if not 1 <= self.importance <= 5:
            raise ValueError("Importance must be between 1 and 5.")
        if self.revision < 1:
            raise ValueError("Revision must be at least 1.")
        if self.relevant_from and self.relevant_until:
            if self.relevant_until < self.relevant_from:
                raise ValueError(
                    "relevant_until cannot precede relevant_from."
                )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation of this record."""
        return {
            "id": self.id,
            "content": self.content,
            "knowledge_type": self.knowledge_type.value,
            "provenance": [
                {
                    "source_type": item.source_type.value,
                    "source_id": item.source_id,
                    "timestamp": item.timestamp,
                    "tool": item.tool,
                    "operation": item.operation,
                    "confidence": item.confidence,
                }
                for item in self.provenance
            ],
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "verification": self.verification.value,
            "importance": self.importance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "relevant_from": self.relevant_from,
            "relevant_until": self.relevant_until,
            "revision": self.revision,
            "evidence_ids": list(self.evidence_ids),
            "tags": list(self.tags),
            "metadata": self.metadata.copy(),
        }
