"""Typed, traceable relationships between Eden knowledge records."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from eden.knowledge.models import Provenance


def utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class RelationshipType(str, Enum):
    """Supported meanings for links between knowledge records."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"
    SUPERSEDES = "supersedes"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    CAUSED_BY = "caused_by"
    SAME_AS = "same_as"
    RELATED_TO = "related_to"


SYMMETRIC_RELATIONSHIPS = frozenset({
    RelationshipType.SAME_AS,
    RelationshipType.RELATED_TO,
})


@dataclass(frozen=True)
class KnowledgeRelationship:
    """A validated, traceable link between two knowledge records.

    Directional relationships preserve the meaning of source and target.
    Symmetric relationships can be traversed in either direction.
    Evidence references identify supporting material; they do not replace
    the provenance describing why this relationship was recorded.
    """

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    provenance: Provenance
    id: str = field(default_factory=lambda: str(uuid4()))
    confidence: float | None = None
    created_at: str = field(default_factory=utc_now)
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("source_id must be a non-empty string")

        if not isinstance(self.target_id, str) or not self.target_id.strip():
            raise ValueError("target_id must be a non-empty string")

        if self.source_id == self.target_id:
            raise ValueError("A relationship cannot connect a record to itself")

        if not isinstance(self.relationship_type, RelationshipType):
            raise ValueError("relationship_type must be a RelationshipType")

        if not isinstance(self.provenance, Provenance):
            raise ValueError("provenance must be a Provenance record")

        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id must be a non-empty string")

        if self.confidence is not None:
            if isinstance(self.confidence, bool) or not isinstance(
                self.confidence, (int, float)
            ):
                raise ValueError("confidence must be numeric or None")
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("confidence must be between 0 and 1")

        if not isinstance(self.evidence_ids, tuple):
            raise ValueError("evidence_ids must be a tuple")

        if any(not isinstance(item, str) or not item.strip()
               for item in self.evidence_ids):
            raise ValueError("evidence IDs must be non-empty strings")

    @property
    def is_symmetric(self) -> bool:
        """Whether this relationship has the same meaning in either direction."""
        return self.relationship_type in SYMMETRIC_RELATIONSHIPS

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "provenance": {
                "source_type": self.provenance.source_type.value,
                "source_id": self.provenance.source_id,
                "timestamp": self.provenance.timestamp,
                "tool": self.provenance.tool,
                "operation": self.provenance.operation,
                "confidence": self.provenance.confidence,
            },
            "confidence": self.confidence,
            "created_at": self.created_at,
            "evidence_ids": list(self.evidence_ids),
            "metadata": self.metadata,
        }
