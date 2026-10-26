"""Acceptance tests for Eden's canonical knowledge model."""

import unittest

from eden.knowledge.models import Evidence, KnowledgeRecord, Provenance
from eden.knowledge.types import (
    ConfidenceLevel,
    KnowledgeType,
    SourceType,
    VerificationStatus,
)


class KnowledgeModelTests(unittest.TestCase):
    def setUp(self):
        self.source = Provenance(
            source_type=SourceType.USER,
            source_id="acceptance-test",
            confidence=1.0,
        )

    def test_record_has_stable_identity_and_serializes_types(self):
        record = KnowledgeRecord(
            content="Eden connects related knowledge.",
            knowledge_type=KnowledgeType.FACT,
            provenance=[self.source],
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            verification=VerificationStatus.SUPPORTED,
        )

        result = record.to_dict()

        self.assertTrue(result["id"])
        self.assertEqual(result["knowledge_type"], "fact")
        self.assertEqual(result["confidence_level"], "high")
        self.assertEqual(result["verification"], "supported")
        self.assertEqual(result["provenance"][0]["source_id"], "acceptance-test")

    def test_knowledge_categories_remain_distinct(self):
        self.assertNotEqual(KnowledgeType.FACT, KnowledgeType.HYPOTHESIS)
        self.assertNotEqual(KnowledgeType.DECISION, KnowledgeType.INSTRUCTION)
        self.assertNotEqual(KnowledgeType.EXPERIENCE, KnowledgeType.EVENT)

    def test_rejects_invalid_confidence_and_importance(self):
        with self.assertRaises(ValueError):
            KnowledgeRecord(
                content="Invalid confidence",
                knowledge_type=KnowledgeType.HYPOTHESIS,
                provenance=[self.source],
                confidence=1.5,
            )

        with self.assertRaises(ValueError):
            KnowledgeRecord(
                content="Invalid importance",
                knowledge_type=KnowledgeType.FACT,
                provenance=[self.source],
                importance=0,
            )

    def test_rejects_empty_provenance_and_evidence(self):
        with self.assertRaises(ValueError):
            Provenance(source_type=SourceType.USER, source_id=" ")

        with self.assertRaises(ValueError):
            Evidence(id="evidence-1", source=self.source, excerpt=" ")

    def test_relevant_time_range_must_be_ordered(self):
        with self.assertRaises(ValueError):
            KnowledgeRecord(
                content="Time-bound knowledge",
                knowledge_type=KnowledgeType.FACT,
                provenance=[self.source],
                relevant_from="2030-01-01",
                relevant_until="2029-01-01",
            )


if __name__ == "__main__":
    unittest.main()
