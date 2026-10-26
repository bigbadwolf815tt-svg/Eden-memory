"""Persistent, append-only revision history for Eden knowledge records."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def ensure_revision_schema(connection: sqlite3.Connection) -> None:
    """Create revision storage without altering existing Eden tables."""
    connection.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            revision INTEGER NOT NULL CHECK (revision >= 1),
            snapshot_json TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT 'update',
            recorded_at TEXT NOT NULL,
            UNIQUE(record_id, revision)
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_knowledge_revisions_record
        ON knowledge_revisions(record_id, revision)
    """)


def save_revision(
    connection: sqlite3.Connection,
    record: Any,
    reason: str = "update",
) -> int:
    """Persist an immutable snapshot of a KnowledgeRecord."""
    from eden.knowledge.models import KnowledgeRecord

    if not isinstance(record, KnowledgeRecord):
        raise TypeError("record must be a KnowledgeRecord")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")

    ensure_revision_schema(connection)
    snapshot = json.dumps(
        record.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    timestamp = datetime.now(timezone.utc).isoformat()

    cursor = connection.execute(
        """
        INSERT INTO knowledge_revisions
            (record_id, revision, snapshot_json, reason, recorded_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (record.id, record.revision, snapshot, reason.strip(), timestamp),
    )
    return int(cursor.lastrowid)


def get_revision_history(
    connection: sqlite3.Connection,
    record_id: str,
) -> list[dict[str, Any]]:
    """Return a record's snapshots in ascending revision order."""
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a non-empty string")

    ensure_revision_schema(connection)
    rows = connection.execute(
        """
        SELECT revision, snapshot_json, reason, recorded_at
        FROM knowledge_revisions
        WHERE record_id = ?
        ORDER BY revision ASC
        """,
        (record_id,),
    ).fetchall()

    return [
        {
            "record_id": record_id,
            "revision": int(row["revision"]),
            "snapshot": json.loads(row["snapshot_json"]),
            "reason": row["reason"],
            "recorded_at": row["recorded_at"],
        }
        for row in rows
    ]


def get_revision(
    connection: sqlite3.Connection,
    record_id: str,
    revision: int,
) -> dict[str, Any] | None:
    """Retrieve one historical snapshot."""
    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a non-empty string")
    if not isinstance(revision, int) or revision < 1:
        raise ValueError("revision must be a positive integer")

    ensure_revision_schema(connection)
    row = connection.execute(
        """
        SELECT revision, snapshot_json, reason, recorded_at
        FROM knowledge_revisions
        WHERE record_id = ? AND revision = ?
        """,
        (record_id, revision),
    ).fetchone()

    if row is None:
        return None

    return {
        "record_id": record_id,
        "revision": int(row["revision"]),
        "snapshot": json.loads(row["snapshot_json"]),
        "reason": row["reason"],
        "recorded_at": row["recorded_at"],
    }
