"""Acceptance tests for persistent knowledge relationships."""

import tempfile
import unittest
from pathlib import Path

from eden.database import connect
from eden.graph.graph_store import (
    get_relationship,
    get_relationships_for_record,
    save_relationship,
)
from eden.graph.relationships import KnowledgeRelationship, RelationshipType
from eden.knowledge.models import Provenance
from eden.knowledge.types import SourceType
from eden.schema import initialize


class GraphStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary.name) / "eden.db"
        self.connection = connect(self.db_path)
        initialize(self.connection)

        # Relationships must connect records that actually exist.
        from eden.knowledge.models import KnowledgeRecord, Provenance
        from eden.knowledge.store import save_knowledge_record
        from eden.knowledge.types import KnowledgeType, SourceType

        for record_id in ("knowledge-alpha", "knowledge-beta"):
            save_knowledge_record(
                self.connection,
                KnowledgeRecord(
                    id=record_id,
                    content=f"Test knowledge record {record_id}",
                    knowledge_type=KnowledgeType.FACT,
                    provenance=[
                        Provenance(
                            source_type=SourceType.USER,
                            source_id="graph-store-test",
                        )
                    ],
                ),
            )
        self.connection.commit()

        self.relationship = KnowledgeRelationship(
            id="relationship-test-001",
            source_id="knowledge-alpha",
            target_id="knowledge-beta",
            relationship_type=RelationshipType.SUPPORTS,
            provenance=Provenance(
                source_type=SourceType.USER,
                source_id="graph-store-test",
                tool="unittest",
                operation="create_relationship",
                confidence=0.95,
            ),
            confidence=0.9,
            evidence_ids=("evidence-1", "evidence-2"),
            metadata={"purpose": "persistence-test"},
        )

    def tearDown(self):
        self.connection.close()
        self.temporary.cleanup()

    def test_save_and_retrieve_preserves_relationship_details(self):
        save_relationship(self.connection, self.relationship)
        self.connection.commit()

        result = get_relationship(self.connection, self.relationship.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.to_dict(), self.relationship.to_dict())

    def test_relationship_survives_database_reopen(self):
        save_relationship(self.connection, self.relationship)
        self.connection.commit()
        self.connection.close()

        self.connection = connect(self.db_path)
        result = get_relationship(self.connection, self.relationship.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.source_id, "knowledge-alpha")
        self.assertEqual(result.target_id, "knowledge-beta")
        self.assertEqual(result.provenance.source_id, "graph-store-test")
        self.assertEqual(result.evidence_ids, ("evidence-1", "evidence-2"))

    def test_lookup_finds_relationship_from_either_endpoint(self):
        save_relationship(self.connection, self.relationship)
        self.connection.commit()

        from_source = get_relationships_for_record(
            self.connection, "knowledge-alpha"
        )
        from_target = get_relationships_for_record(
            self.connection, "knowledge-beta"
        )

        self.assertEqual([item.id for item in from_source], [self.relationship.id])
        self.assertEqual([item.id for item in from_target], [self.relationship.id])

    def test_lookup_can_filter_by_relationship_type(self):
        save_relationship(self.connection, self.relationship)
        self.connection.commit()

        results = get_relationships_for_record(
            self.connection,
            "knowledge-alpha",
            RelationshipType.CONTRADICTS,
        )

        self.assertEqual(results, [])

    def test_rejects_relationship_with_missing_endpoint(self):
        invalid = KnowledgeRelationship(
            id="relationship-missing-endpoint",
            source_id="knowledge-alpha",
            target_id="record-that-does-not-exist",
            relationship_type=RelationshipType.SUPPORTS,
            provenance=Provenance(
                source_type=SourceType.USER,
                source_id="graph-store-test",
                tool="unittest",
                operation="create_relationship",
                confidence=0.95,
            ),
            confidence=0.9,
        )

        with self.assertRaisesRegex(ValueError, "endpoints"):
            save_relationship(self.connection, invalid)

    def test_duplicate_relationship_id_is_rejected(self):
        save_relationship(self.connection, self.relationship)

        with self.assertRaises(Exception):
            save_relationship(self.connection, self.relationship)

    def test_empty_record_id_is_rejected(self):
        with self.assertRaises(ValueError):
            get_relationships_for_record(self.connection, "  ")


if __name__ == "__main__":
    unittest.main()
