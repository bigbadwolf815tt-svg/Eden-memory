"""Persistent storage for traceable knowledge relationships."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from eden.graph.relationships import KnowledgeRelationship, RelationshipType
from eden.knowledge.models import Provenance
from eden.knowledge.types import SourceType


def _relationship_from_row(row: sqlite3.Row) -> KnowledgeRelationship:
    """Rebuild a validated relationship from its stored representation."""
    provenance_data = json.loads(row["provenance_json"])

    provenance = Provenance(
        source_type=SourceType(provenance_data["source_type"]),
        source_id=provenance_data["source_id"],
        timestamp=provenance_data["timestamp"],
        tool=provenance_data["tool"],
        operation=provenance_data["operation"],
        confidence=provenance_data["confidence"],
    )

    return KnowledgeRelationship(
        id=row["id"],
        source_id=row["source_id"],
        target_id=row["target_id"],
        relationship_type=RelationshipType(row["relationship_type"]),
        provenance=provenance,
        confidence=row["confidence"],
        created_at=row["created_at"],
        evidence_ids=tuple(json.loads(row["evidence_ids_json"])),
        metadata=json.loads(row["metadata_json"]),
    )


def save_relationship(
    connection: sqlite3.Connection,
    relationship: KnowledgeRelationship,
) -> str:
    """Persist a relationship and return its stable ID.

    The caller owns the connection and its transaction.
    Duplicate IDs and invalid database values are rejected by SQLite.
    """
    if not isinstance(relationship, KnowledgeRelationship):
        raise TypeError("relationship must be a KnowledgeRelationship")

    endpoints = connection.execute(
        """
        SELECT id FROM knowledge_records
        WHERE id IN (?, ?)
        """,
        (relationship.source_id, relationship.target_id),
    ).fetchall()

    if len(endpoints) != 2:
        raise ValueError(
            "Both relationship endpoints must be existing knowledge records"
        )

    provenance: dict[str, Any] = {
        "source_type": relationship.provenance.source_type.value,
        "source_id": relationship.provenance.source_id,
        "timestamp": relationship.provenance.timestamp,
        "tool": relationship.provenance.tool,
        "operation": relationship.provenance.operation,
        "confidence": relationship.provenance.confidence,
    }

    connection.execute(
        """
        INSERT INTO knowledge_relationships (
            id, source_id, target_id, relationship_type,
            provenance_json, confidence, created_at,
            evidence_ids_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            relationship.id,
            relationship.source_id,
            relationship.target_id,
            relationship.relationship_type.value,
            json.dumps(provenance, ensure_ascii=False, sort_keys=True),
            relationship.confidence,
            relationship.created_at,
            json.dumps(list(relationship.evidence_ids), ensure_ascii=False),
            json.dumps(
                relationship.metadata, ensure_ascii=False, sort_keys=True
            ),
        ),
    )
    return relationship.id


def get_relationship(
    connection: sqlite3.Connection,
    relationship_id: str,
) -> KnowledgeRelationship | None:
    """Retrieve a relationship by its stable ID."""
    row = connection.execute(
        "SELECT * FROM knowledge_relationships WHERE id = ?",
        (relationship_id,),
    ).fetchone()

    return _relationship_from_row(row) if row is not None else None


def get_relationships_for_record(
    connection: sqlite3.Connection,
    record_id: str,
    relationship_type: RelationshipType | None = None,
) -> list[KnowledgeRelationship]:
    """Return relationships touching a record, in either direction."""
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a non-empty string")

    if relationship_type is not None and not isinstance(
        relationship_type, RelationshipType
    ):
        raise TypeError("relationship_type must be a RelationshipType or None")

    query = """
        SELECT * FROM knowledge_relationships
        WHERE (source_id = ? OR target_id = ?)
    """
    parameters: list[Any] = [record_id, record_id]

    if relationship_type is not None:
        query += " AND relationship_type = ?"
        parameters.append(relationship_type.value)

    query += " ORDER BY created_at, id"

    rows = connection.execute(query, parameters).fetchall()
    return [_relationship_from_row(row) for row in rows]
