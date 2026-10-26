"""SQLite database foundation for Eden's local-first memory engine."""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB = DATA_DIR / "eden.db"


def connect(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    """Open a persistent SQLite database and enable foreign keys."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
