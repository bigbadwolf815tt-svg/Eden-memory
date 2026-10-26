import unittest

from eden.graph.relationships import (
    KnowledgeRelationship,
    RelationshipType,
)
from eden.knowledge.models import Provenance
from eden.knowledge.types import SourceType


def make_provenance():
    return Provenance(
        source_type=SourceType.USER,
        source_id="test-source",
    )


class RelationshipTests(unittest.TestCase):
    def make_relationship(self, **overrides):
        values = {
            "source_id": "record-a",
            "target_id": "record-b",
            "relationship_type": RelationshipType.DERIVED_FROM,
            "provenance": make_provenance(),
            "confidence": 0.9,
            "evidence_ids": ("evidence-1",),
        }
        values.update(overrides)
        return KnowledgeRelationship(**values)

    def test_creates_traceable_relationship(self):
        relation = self.make_relationship()

        self.assertTrue(relation.id)
        self.assertEqual(relation.source_id, "record-a")
        self.assertEqual(relation.target_id, "record-b")
        self.assertEqual(relation.relationship_type,
                         RelationshipType.DERIVED_FROM)
        self.assertEqual(relation.provenance.source_id, "test-source")

    def test_serialization_preserves_relationship_and_provenance(self):
        relation = self.make_relationship()
        result = relation.to_dict()

        self.assertEqual(result["relationship_type"], "derived_from")
        self.assertEqual(result["source_id"], "record-a")
        self.assertEqual(result["target_id"], "record-b")
        self.assertEqual(result["provenance"]["source_type"], "user")
        self.assertEqual(result["evidence_ids"], ["evidence-1"])

    def test_symmetric_relationships_are_identified(self):
        same_as = self.make_relationship(
            relationship_type=RelationshipType.SAME_AS
        )
        related_to = self.make_relationship(
            relationship_type=RelationshipType.RELATED_TO
        )
        depends_on = self.make_relationship(
            relationship_type=RelationshipType.DEPENDS_ON
        )

        self.assertTrue(same_as.is_symmetric)
        self.assertTrue(related_to.is_symmetric)
        self.assertFalse(depends_on.is_symmetric)

    def test_rejects_empty_ids_and_self_relationships(self):
        with self.assertRaises(ValueError):
            self.make_relationship(source_id=" ")

        with self.assertRaises(ValueError):
            self.make_relationship(target_id="record-a")

    def test_rejects_invalid_confidence(self):
        for confidence in (-0.1, 1.1, True, "high"):
            with self.subTest(confidence=confidence):
                with self.assertRaises(ValueError):
                    self.make_relationship(confidence=confidence)

    def test_rejects_invalid_type_and_provenance(self):
        with self.assertRaises(ValueError):
            self.make_relationship(relationship_type="derived_from")

        with self.assertRaises(ValueError):
            self.make_relationship(provenance=None)

    def test_rejects_empty_evidence_ids(self):
        with self.assertRaises(ValueError):
            self.make_relationship(evidence_ids=("",))


if __name__ == "__main__":
    unittest.main()
