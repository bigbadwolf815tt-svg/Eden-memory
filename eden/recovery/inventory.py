"""Read-only inventory and integrity verification for Eden database snapshots."""

from pathlib import Path
from typing import Any

from eden.recovery.database_snapshot import verify_database_snapshot


def inventory_snapshots(directory: str | Path) -> list[dict[str, Any]]:
    """List snapshot files and report their verification status."""
    root = Path(directory)

    if not root.exists():
        return []

    if not root.is_dir():
        raise NotADirectoryError(f"Snapshot location is not a directory: {root}")

    results: list[dict[str, Any]] = []

    for manifest in sorted(root.glob("*.manifest.json")):
        backup = Path(str(manifest)[:-len(".manifest.json")])

        item: dict[str, Any] = {
            "snapshot": str(backup),
            "manifest": str(manifest),
            "exists": backup.is_file(),
            "verified": False,
            "error": None,
        }

        if not backup.is_file():
            item["error"] = "Snapshot file is missing"
        else:
            try:
                verification = verify_database_snapshot(backup)
                item["verified"] = verification is not False
                if isinstance(verification, dict):
                    item["verification"] = verification
            except Exception as exc:
                item["error"] = f"{type(exc).__name__}: {exc}"

        results.append(item)

    return results


def verify_snapshot_inventory(directory: str | Path) -> dict[str, Any]:
    """Return a concise integrity summary without altering snapshot files."""
    snapshots = inventory_snapshots(directory)
    verified = sum(1 for item in snapshots if item["verified"])
    failed = len(snapshots) - verified

    return {
        "directory": str(Path(directory)),
        "snapshot_count": len(snapshots),
        "verified_count": verified,
        "failed_count": failed,
        "healthy": bool(snapshots) and failed == 0,
        "snapshots": snapshots,
    }
