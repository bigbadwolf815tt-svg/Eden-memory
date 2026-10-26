# Eden Knowledge Model

## Purpose

Eden represents knowledge as structured, traceable records rather than
unattributed text alone. The model is independent of storage so that the
database can evolve without silently changing the meaning of a record.

## Knowledge classifications

- **Fact:** a claim presented as factual, subject to evidence and correction.
- **Preference:** a stated or observed preference.
- **Experience:** an event or experience associated with a person or context.
- **Decision:** a decision and its recorded rationale.
- **Hypothesis:** a tentative claim that has not been established.
- **Instruction:** a constraint or directive.
- **Project record:** information about a project, its state, or its history.
- **Concept:** an abstract idea or definition.
- **Entity:** an identifiable person, place, organization, or thing.
- **Event:** an occurrence situated in time.
- **Document:** a source artifact or document record.
- **Procedure:** a repeatable sequence of steps.

Classification does not itself establish truth.

## Identity and time

Each record has a stable identifier, creation and update timestamps, and a
revision number. Relevant-time fields describe when the knowledge applies,
which may differ from when Eden recorded it.

## Provenance and evidence

Provenance records the source type, source identifier, timestamp, and
optional tool, operation, and confidence. Evidence is represented separately
so that supporting and challenging material can be retained without
rewriting the original source.

Inferred claims must not be represented as directly observed facts merely
because an inference seems plausible.

## Confidence and verification

Numeric confidence, qualitative confidence, and verification status are
separate fields. Confidence expresses degree of belief; verification status
records the current review state. Neither substitutes for preserving evidence.

## Importance

Importance ranges from 1 to 5. It is a prioritization signal, not a measure
of truth or evidential strength.

## Relationships and history

Relationships between records will be stored as typed, traceable links.
Corrections and superseded claims must retain their history instead of
silently erasing the earlier state.

## Persistence contract

These Python models define the logical contract. Database migrations,
repositories, relationship storage, history, and retrieval must explicitly
map to this contract. A model being constructible does not imply that all
of its fields are already persisted.
