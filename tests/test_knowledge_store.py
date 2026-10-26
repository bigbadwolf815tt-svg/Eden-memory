"""Tests for persistent canonical knowledge records."""

import tempfile
import unittest
from pathlib import Path

from eden.database import connect
from eden.knowledge.models import KnowledgeRecord, Provenance
from eden.knowledge.store import (
    count_knowledge_records,
    get_knowledge_record,
    save_knowledge_record,
)
from eden.knowledge.types import (
    ConfidenceLevel,
    KnowledgeType,
    SourceType,
    VerificationStatus,
)
from eden.schema import initialize


class KnowledgeStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "knowledge.db"
        self.connection = connect(self.db_path)
        initialize(self.connection)

        self.record = KnowledgeRecord(
            id="knowledge-persistent-test",
            content="EDEN preserves traceable knowledge.",
            knowledge_type=KnowledgeType.FACT,
            provenance=[
                Provenance(
                    source_type=SourceType.USER,
                    source_id="knowledge-store-test",
                    tool="unittest",
                    operation="save_record",
                    confidence=0.98,
                )
            ],
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            verification=VerificationStatus.SUPPORTED,
            importance=5,
            evidence_ids=["evidence-alpha"],
            tags=["eden", "persistence"],
            metadata={"purpose": "round-trip-test"},
        )

    def tearDown(self):
        self.connection.close()
        self.temp_dir.cleanup()

    def test_save_and_retrieve_preserves_record(self):
        record_id = save_knowledge_record(self.connection, self.record)
        self.connection.commit()

        result = get_knowledge_record(self.connection, record_id)

        self.assertIsNotNone(result)
        self.assertEqual(result.to_dict(), self.record.to_dict())

    def test_record_survives_database_reopen(self):
        save_knowledge_record(self.connection, self.record)
        self.connection.commit()
        self.connection.close()

        self.connection = connect(self.db_path)
        initialize(self.connection)

        result = get_knowledge_record(
            self.connection, "knowledge-persistent-test"
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.content, self.record.content)
        self.assertEqual(result.provenance[0].source_id, "knowledge-store-test")

    def test_missing_record_returns_none(self):
        self.assertIsNone(get_knowledge_record(self.connection, "missing-id"))

    def test_duplicate_id_is_rejected(self):
        save_knowledge_record(self.connection, self.record)

        with self.assertRaises(Exception):
            save_knowledge_record(self.connection, self.record)

    def test_record_count(self):
        self.assertEqual(count_knowledge_records(self.connection), 0)
        save_knowledge_record(self.connection, self.record)
        self.assertEqual(count_knowledge_records(self.connection), 1)


if __name__ == "__main__":
    unittest.main()
