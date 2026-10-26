"""Core memory operations for Eden."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from eden.schema import initialize_schema

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "eden.db"


def get_connection(
    db_path: str | Path | None = None,
) -> sqlite3.Connection:
    """Open an initialized Eden database."""
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    initialize_schema(connection)
    return connection


def _memory_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a database row into a dictionary."""
    memory = dict(row)
    try:
        memory["metadata"] = json.loads(memory.pop("metadata_json"))
    except (json.JSONDecodeError, TypeError):
        memory["metadata"] = {}
    return memory


def save_memory(
    content: str,
    category: str = "general",
    source: str = "user",
    importance: int = 3,
    confidence: float = 1.0,
    metadata: dict[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Save a memory and return the stored record."""
    content = content.strip()
    category = category.strip()
    source = source.strip()

    if not content:
        raise ValueError("Memory content cannot be empty.")
    if not category:
        raise ValueError("Memory category cannot be empty.")
    if not source:
        raise ValueError("Memory source cannot be empty.")
    if not 1 <= importance <= 5:
        raise ValueError("Importance must be between 1 and 5.")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("Confidence must be between 0.0 and 1.0.")

    metadata_json = json.dumps(
        metadata or {},
        ensure_ascii=False,
        sort_keys=True,
    )

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO memories
                (content, category, source, importance, confidence,
                 metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                content,
                category,
                source,
                importance,
                confidence,
                metadata_json,
            ),
        )
        row = connection.execute(
            "SELECT * FROM memories WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return _memory_dict(row)


def get_memory(
    memory_id: int,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Retrieve a memory by ID and record that it was accessed."""
    with get_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE memories
            SET access_count = access_count + 1,
                last_accessed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ? AND archived = 0
            """,
            (memory_id,),
        )
        row = connection.execute(
            "SELECT * FROM memories WHERE id = ? AND archived = 0",
            (memory_id,),
        ).fetchone()

        return _memory_dict(row) if row else None


def search_memories(
    query: str,
    limit: int = 10,
    category: str | None = None,
    include_archived: bool = False,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Search memory content using case-insensitive SQLite text matching."""
    query = query.strip()
    if not query:
        return []
    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    escaped_query = (
        query.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

    conditions = ["content LIKE ? ESCAPE '\\'"]
    parameters: list[Any] = [f"%{escaped_query}%"]

    if category is not None:
        conditions.append("category = ?")
        parameters.append(category)

    if not include_archived:
        conditions.append("archived = 0")

    parameters.append(limit)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT * FROM memories
            WHERE {" AND ".join(conditions)}
            ORDER BY importance DESC, updated_at DESC, id DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()

        return [_memory_dict(row) for row in rows]


def update_memory(
    memory_id: int,
    db_path: str | Path | None = None,
    **updates: Any,
) -> dict[str, Any] | None:
    """Update supported fields on an existing, active memory."""
    allowed_fields = {
        "content",
        "category",
        "source",
        "importance",
        "confidence",
        "metadata",
    }

    unknown = set(updates) - allowed_fields
    if unknown:
        raise ValueError(f"Unsupported fields: {', '.join(sorted(unknown))}")
    if not updates:
        return get_memory(memory_id, db_path)

    values: dict[str, Any] = {}

    for field, value in updates.items():
        if field in {"content", "category", "source"}:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string.")
            values[field] = value.strip()
        elif field == "importance":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError("Importance must be an integer from 1 to 5.")
            if not 1 <= value <= 5:
                raise ValueError("Importance must be between 1 and 5.")
            values[field] = value
        elif field == "confidence":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError("Confidence must be a number from 0 to 1.")
            if not 0.0 <= value <= 1.0:
                raise ValueError("Confidence must be between 0.0 and 1.0.")
            values[field] = float(value)
        elif field == "metadata":
            if not isinstance(value, dict):
                raise ValueError("Metadata must be a dictionary.")
            values["metadata_json"] = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
            )

    assignments = [
        f"{field} = ?" for field in values
    ]
    assignments.append(
        "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
    )
    parameters = list(values.values()) + [memory_id]

    with get_connection(db_path) as connection:
        connection.execute(
            f"""
            UPDATE memories
            SET {", ".join(assignments)}
            WHERE id = ? AND archived = 0
            """,
            parameters,
        )
        row = connection.execute(
            "SELECT * FROM memories WHERE id = ? AND archived = 0",
            (memory_id,),
        ).fetchone()

        return _memory_dict(row) if row else None


def archive_memory(
    memory_id: int,
    db_path: str | Path | None = None,
) -> bool:
    """Archive a memory without permanently deleting it."""
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE memories
            SET archived = 1,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ? AND archived = 0
            """,
            (memory_id,),
        )
        return cursor.rowcount > 0


def restore_memory(
    memory_id: int,
    db_path: str | Path | None = None,
) -> bool:
    """Restore an archived memory."""
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE memories
            SET archived = 0,
                updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ? AND archived = 1
            """,
            (memory_id,),
        )
        return cursor.rowcount > 0
