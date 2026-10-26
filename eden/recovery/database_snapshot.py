"""Verified, atomic SQLite database snapshots for Eden."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_database(path: Path) -> None:
    """Reject corrupt or incomplete SQLite databases."""
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Database is missing or empty: {path}")

    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            raise ValueError(f"SQLite integrity check failed: {result}")
    finally:
        connection.close()


def create_database_snapshot(
    database_path: str | Path,
    backup_path: str | Path,
) -> dict[str, Any]:
    """Create a consistent, verified snapshot of the complete database.

    Existing backups are never overwritten. A JSON manifest records the
    database checksum, size, timestamp, and SQLite integrity result.
    """
    source = Path(database_path).expanduser().resolve()
    destination = Path(backup_path).expanduser().resolve()
    manifest_path = Path(str(destination) + ".manifest.json")

    if not source.is_file():
        raise FileNotFoundError(f"Source database not found: {source}")
    if source == destination:
        raise ValueError("Backup destination must differ from source database.")
    if destination.exists() or manifest_path.exists():
        raise FileExistsError("Backup or manifest already exists; refusing to overwrite.")

    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=".eden-snapshot-",
        suffix=".sqlite3",
        dir=destination.parent,
    )
    os.close(fd)
    temporary = Path(temporary_name)
    temporary_manifest = Path(str(temporary) + ".manifest.json")

    try:
        source_connection = sqlite3.connect(
            f"file:{source}?mode=ro", uri=True, timeout=30
        )
        target_connection = sqlite3.connect(str(temporary), timeout=30)

        try:
            source_connection.backup(target_connection)
            target_connection.commit()
        finally:
            target_connection.close()
            source_connection.close()

        _check_database(temporary)

        manifest = {
            "format": "eden-sqlite-snapshot-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_filename": destination.name,
            "size_bytes": temporary.stat().st_size,
            "sha256": _sha256(temporary),
            "integrity_check": "ok",
        }

        with temporary_manifest.open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())

        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())

        with open(temporary, 'rb') as src, open(destination, 'xb') as dst:
            import shutil
            shutil.copyfileobj(src, dst)
            dst.flush()
        try:
            with open(temporary_manifest, 'rb') as src, open(manifest_path, 'xb') as dst:
                import shutil
                shutil.copyfileobj(src, dst)
                dst.flush()
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        return manifest

    finally:
        temporary.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)


def verify_database_snapshot(backup_path: str | Path) -> dict[str, Any]:
    """Verify a snapshot's manifest, checksum, and SQLite integrity."""
    backup = Path(backup_path).expanduser().resolve()
    manifest_path = Path(str(backup) + ".manifest.json")

    if not backup.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("Snapshot database or manifest is missing.")

    with manifest_path.open("r", encoding="utf-8") as stream:
        manifest = json.load(stream)

    if manifest.get("format") != "eden-sqlite-snapshot-v1":
        raise ValueError("Unsupported snapshot manifest format.")
    if manifest.get("sha256") != _sha256(backup):
        raise ValueError("Snapshot checksum mismatch.")
    if manifest.get("size_bytes") != backup.stat().st_size:
        raise ValueError("Snapshot size mismatch.")

    _check_database(backup)
    return manifest


def restore_database_snapshot(
    backup_path: str | Path,
    destination_path: str | Path,
) -> dict[str, Any]:
    """Restore a verified snapshot without exposing a partial database.

    The destination must not be the live source database unless the caller
    deliberately supplies that path. An existing destination is preserved
    until the restored temporary database has passed integrity checks.
    """
    backup = Path(backup_path).expanduser().resolve()
    destination = Path(destination_path).expanduser().resolve()

    manifest = verify_database_snapshot(backup)

    if backup == destination:
        raise ValueError("Restore destination must differ from the backup.")
    if destination.exists() and destination.is_dir():
        raise IsADirectoryError(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=".eden-restore-",
        suffix=".sqlite3",
        dir=destination.parent,
    )
    os.close(fd)
    temporary = Path(temporary_name)

    try:
        backup_connection = sqlite3.connect(
            f"file:{backup}?mode=ro", uri=True, timeout=30
        )
        restored_connection = sqlite3.connect(str(temporary), timeout=30)

        try:
            backup_connection.backup(restored_connection)
            restored_connection.commit()
        finally:
            restored_connection.close()
            backup_connection.close()

        _check_database(temporary)
        os.replace(temporary, destination)

        return {
            "restored_to": str(destination),
            "sha256": _sha256(destination),
            "integrity_check": "ok",
            "snapshot_created_at": manifest["created_at"],
        }

    finally:
        temporary.unlink(missing_ok=True)


# Storage-aware safety wrappers. Keep the original implementations as the
# underlying operations so existing snapshot behavior remains intact.
_create_database_snapshot_impl = create_database_snapshot
_restore_database_snapshot_impl = restore_database_snapshot


def create_database_snapshot(database_path, backup_path):
    """Create a verified snapshot only when the storage reserve is respected."""
    from eden.maintenance.storage_guard import require_storage_capacity

    source = Path(database_path)
    destination = Path(backup_path)

    if not source.is_file():
        raise FileNotFoundError(f"Database does not exist: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    required_bytes = source.stat().st_size

    require_storage_capacity(
        destination.parent,
        required_bytes,
    )

    return _create_database_snapshot_impl(source, destination)


def restore_database_snapshot(backup_path, destination_path):
    """Verify a snapshot and preserve any existing destination before restore."""
    from eden.maintenance.storage_guard import require_storage_capacity
    from datetime import datetime, timezone

    backup = Path(backup_path)
    destination = Path(destination_path)

    # Reject invalid snapshots before touching the destination.
    verify_database_snapshot(backup)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if not destination.is_file():
            raise OSError(
                f"Restore destination is not a regular file: {destination}"
            )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        safety_copy = destination.with_name(
            f"{destination.name}.pre-restore-{timestamp}.sqlite3"
        )

        require_storage_capacity(
            destination.parent,
            destination.stat().st_size,
        )

        # If preservation fails, the restore must not proceed.
        _create_database_snapshot_impl(destination, safety_copy)

    return _restore_database_snapshot_impl(backup, destination)
