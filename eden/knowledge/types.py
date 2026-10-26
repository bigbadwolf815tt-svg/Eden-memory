"""Canonical classifications used throughout Eden."""

from enum import Enum


class KnowledgeType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EXPERIENCE = "experience"
    DECISION = "decision"
    HYPOTHESIS = "hypothesis"
    INSTRUCTION = "instruction"
    PROJECT_RECORD = "project_record"
    CONCEPT = "concept"
    ENTITY = "entity"
    EVENT = "event"
    DOCUMENT = "document"
    PROCEDURE = "procedure"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNKNOWN = "unknown"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class SourceType(str, Enum):
    USER = "user"
    CONVERSATION = "conversation"
    DOCUMENT = "document"
    TOOL = "tool"
    EXTERNAL_SOURCE = "external_source"
    SYSTEM = "system"
    INFERENCE = "inference"
