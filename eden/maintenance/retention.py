"""Safe retention policy for verified Eden database snapshots."""

from pathlib import Path
from typing import Any

from eden.recovery.inventory import inventory_snapshots


def prune_snapshots(
    directory: str | Path,
    *,
    keep_verified: int = 3,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Plan or remove old verified snapshots, retaining the newest verified set.

    Unverified snapshots are never deleted automatically.
    Dry-run is the default; deletion requires explicit dry_run=False.
    """
    if isinstance(keep_verified, bool) or not isinstance(keep_verified, int):
        raise TypeError("keep_verified must be an integer")
    if keep_verified < 1:
        raise ValueError("keep_verified must be at least 1")

    root = Path(directory)
    if not root.exists():
        return {
            "directory": str(root),
            "dry_run": dry_run,
            "kept": [],
            "candidates": [],
            "deleted": [],
            "errors": [],
        }
    if not root.is_dir():
        raise NotADirectoryError(f"Snapshot location is not a directory: {root}")

    inventory = inventory_snapshots(root)
    verified = []

    for item in inventory:
        if not item["verified"]:
            continue
        backup = Path(item["snapshot"])
        manifest = Path(item["manifest"])
        try:
            modified = max(backup.stat().st_mtime, manifest.stat().st_mtime)
        except OSError:
            modified = 0
        verified.append((modified, backup, manifest))

    verified.sort(key=lambda entry: entry[0], reverse=True)
    retained = verified[:keep_verified]
    candidates = verified[keep_verified:]

    deleted: list[str] = []
    errors: list[dict[str, str]] = []

    if not dry_run:
        for _, backup, manifest in candidates:
            try:
                # Reverify immediately before deletion to reduce race risks.
                from eden.recovery.database_snapshot import verify_database_snapshot
                verify_database_snapshot(backup)

                backup.unlink()
                try:
                    manifest.unlink()
                except OSError as exc:
                    errors.append({
                        "path": str(manifest),
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                deleted.append(str(backup))
            except Exception as exc:
                errors.append({
                    "path": str(backup),
                    "error": f"{type(exc).__name__}: {exc}",
                })

    return {
        "directory": str(root),
        "dry_run": dry_run,
        "verified_count": len(verified),
        "kept": [str(backup) for _, backup, _ in retained],
        "candidates": [str(backup) for _, backup, _ in candidates],
        "deleted": deleted,
        "errors": errors,
        "unverified_preserved": [
            item["snapshot"] for item in inventory if not item["verified"]
        ],
    }
