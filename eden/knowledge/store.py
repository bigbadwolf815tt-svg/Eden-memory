"""Persistent storage for canonical Eden knowledge records."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from eden.knowledge.models import KnowledgeRecord, Provenance
from eden.knowledge.types import (
    ConfidenceLevel,
    KnowledgeType,
    SourceType,
    VerificationStatus,
)


def _record_from_row(row: sqlite3.Row) -> KnowledgeRecord:
    """Reconstruct a knowledge record from its database representation."""
    provenance_data = json.loads(row["provenance_json"])

    provenance = [
        Provenance(
            source_type=SourceType(item["source_type"]),
            source_id=item["source_id"],
            timestamp=item["timestamp"],
            tool=item["tool"],
            operation=item["operation"],
            confidence=item["confidence"],
        )
        for item in provenance_data
    ]

    return KnowledgeRecord(
        id=row["id"],
        content=row["content"],
        knowledge_type=KnowledgeType(row["knowledge_type"]),
        provenance=provenance,
        confidence=row["confidence"],
        confidence_level=ConfidenceLevel(row["confidence_level"]),
        verification=VerificationStatus(row["verification"]),
        importance=row["importance"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        relevant_from=row["relevant_from"],
        relevant_until=row["relevant_until"],
        revision=row["revision"],
        evidence_ids=json.loads(row["evidence_ids_json"]),
        tags=json.loads(row["tags_json"]),
        metadata=json.loads(row["metadata_json"]),
    )


def save_knowledge_record(
    connection: sqlite3.Connection,
    record: KnowledgeRecord,
) -> str:
    """Insert a new knowledge record without overwriting an existing ID."""
    if not isinstance(record, KnowledgeRecord):
        raise TypeError("record must be a KnowledgeRecord")

    data = record.to_dict()

    connection.execute(
        """
        INSERT INTO knowledge_records (
            id, content, knowledge_type, provenance_json,
            confidence, confidence_level, verification, importance,
            created_at, updated_at, relevant_from, relevant_until,
            revision, evidence_ids_json, tags_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["id"],
            data["content"],
            data["knowledge_type"],
            json.dumps(data["provenance"], ensure_ascii=False, sort_keys=True),
            data["confidence"],
            data["confidence_level"],
            data["verification"],
            data["importance"],
            data["created_at"],
            data["updated_at"],
            data["relevant_from"],
            data["relevant_until"],
            data["revision"],
            json.dumps(data["evidence_ids"], ensure_ascii=False),
            json.dumps(data["tags"], ensure_ascii=False),
            json.dumps(data["metadata"], ensure_ascii=False, sort_keys=True),
        ),
    )

    return record.id


def get_knowledge_record(
    connection: sqlite3.Connection,
    record_id: str,
) -> KnowledgeRecord | None:
    """Retrieve a knowledge record by stable ID."""
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a non-empty string")

    row = connection.execute(
        "SELECT * FROM knowledge_records WHERE id = ?",
        (record_id,),
    ).fetchone()

    return _record_from_row(row) if row is not None else None


def count_knowledge_records(connection: sqlite3.Connection) -> int:
    """Return the number of persisted canonical knowledge records."""
    row = connection.execute(
        "SELECT COUNT(*) AS total FROM knowledge_records"
    ).fetchone()
    return int(row["total"])


def update_knowledge_record(
    connection: sqlite3.Connection,
    record: KnowledgeRecord,
    reason: str = "update",
) -> int:
    """Atomically preserve the current revision and update a knowledge record."""
    from eden.history.revisions import save_revision

    if not isinstance(record, KnowledgeRecord):
        raise TypeError("record must be a KnowledgeRecord")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")

    current = get_knowledge_record(connection, record.id)
    if current is None:
        raise ValueError(f"Knowledge record does not exist: {record.id}")

    if record.revision != current.revision:
        raise ValueError(
            f"Revision conflict for {record.id}: "
            f"expected {current.revision}, received {record.revision}"
        )

    connection.execute("SAVEPOINT eden_knowledge_update")

    try:
        save_revision(connection, current, reason=reason)
        data = record.to_dict()
        next_revision = current.revision + 1

        cursor = connection.execute(
            """
            UPDATE knowledge_records SET
                content = ?,
                knowledge_type = ?,
                provenance_json = ?,
                confidence = ?,
                confidence_level = ?,
                verification = ?,
                importance = ?,
                updated_at = ?,
                relevant_from = ?,
                relevant_until = ?,
                revision = ?,
                evidence_ids_json = ?,
                tags_json = ?,
                metadata_json = ?
            WHERE id = ? AND revision = ?
            """,
            (
                data["content"],
                data["knowledge_type"],
                json.dumps(
                    data["provenance"], ensure_ascii=False, sort_keys=True
                ),
                data["confidence"],
                data["confidence_level"],
                data["verification"],
                data["importance"],
                data["updated_at"],
                data["relevant_from"],
                data["relevant_until"],
                next_revision,
                json.dumps(data["evidence_ids"], ensure_ascii=False),
                json.dumps(data["tags"], ensure_ascii=False),
                json.dumps(data["metadata"], ensure_ascii=False, sort_keys=True),
                data["id"],
                current.revision,
            ),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "Knowledge record changed during update; retrieve the latest revision."
            )

        connection.execute("RELEASE SAVEPOINT eden_knowledge_update")
        return next_revision

    except Exception:
        connection.execute("ROLLBACK TO SAVEPOINT eden_knowledge_update")
        connection.execute("RELEASE SAVEPOINT eden_knowledge_update")
        raise
