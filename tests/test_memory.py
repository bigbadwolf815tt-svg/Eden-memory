"""Acceptance tests for Eden's memory operations."""

import tempfile
import unittest
from pathlib import Path

from eden.memory import get_memory, save_memory, search_memories


class MemoryTests(unittest.TestCase):
    def test_save_retrieve_and_search(self):
        with tempfile.TemporaryDirectory() as temporary:
            db_path = Path(temporary) / "memory-test.db"

            memory_id = save_memory(
                "Eden connects related knowledge",
                source="acceptance-test",
                db_path=db_path,
            )

            memory = get_memory(memory_id, db_path=db_path)
            self.assertEqual(memory["content"], "Eden connects related knowledge")
            self.assertEqual(memory["source"], "acceptance-test")

            results = search_memories("knowledge", db_path=db_path)
            self.assertTrue(any(item["id"] == memory_id for item in results))

    def test_rejects_empty_memory(self):
        with self.assertRaises(ValueError):
            save_memory("   ", db_path=Path("/tmp/eden-unused-test.db"))

    def test_empty_search_returns_no_results(self):
        self.assertEqual(search_memories("   "), [])


if __name__ == "__main__":
    unittest.main()
