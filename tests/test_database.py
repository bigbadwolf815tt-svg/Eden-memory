"""Acceptance tests for Eden's initial database foundation."""

import tempfile
import unittest
from pathlib import Path

from eden.database import connect
from eden.schema import initialize


class DatabaseTests(unittest.TestCase):
    def test_create_store_search_and_reopen(self):
        with tempfile.TemporaryDirectory() as temporary:
            db_path = Path(temporary) / "eden-test.db"

            connection = connect(db_path)
            initialize(connection)

            cursor = connection.execute(
                """
                INSERT INTO memories (content, memory_type, source)
                VALUES (?, ?, ?)
                """,
                ("Eden remembers connected knowledge", "fact", "acceptance-test"),
            )
            memory_id = cursor.lastrowid
            connection.commit()

            result = connection.execute(
                "SELECT content, memory_type FROM memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
            self.assertEqual(result["content"], "Eden remembers connected knowledge")
            self.assertEqual(result["memory_type"], "fact")

            matches = connection.execute(
                "SELECT rowid FROM memories_fts WHERE memories_fts MATCH ?",
                ("connected",),
            ).fetchall()
            self.assertEqual([row["rowid"] for row in matches], [memory_id])
            connection.close()

            reopened = connect(db_path)
            persisted = reopened.execute(
                "SELECT content FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            self.assertIsNotNone(persisted)
            self.assertEqual(persisted["content"], "Eden remembers connected knowledge")
            reopened.close()


if __name__ == "__main__":
    unittest.main()
