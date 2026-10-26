# Eden Subject Classification Design

## Direction

Eden will use the Dewey Decimal Classification system as the conceptual
foundation for organizing subjects, with a documented extension layer for
personal memory, conversations, project history, and other knowledge-engine
needs.

This is a design decision, not an implemented classification engine.

## Separation of concerns

Subject classification answers: "What subject does this knowledge belong to?"

Knowledge types answer: "What kind of record is this?"

Relationships answer: "How is this record connected to another record?"

Provenance and evidence answer: "Where did this information come from, and
what supports or challenges it?"

A knowledge record may have multiple subject assignments while retaining one
stable identity and its own provenance, verification status, and history.

## Planned capabilities

- Hierarchical decimal subject codes and descriptions.
- Parent-child links between subject categories.
- Multiple subject assignments per knowledge record.
- A documented Eden-specific extension layer.
- Traceability for manual and automatically suggested assignments.
- Validation of codes and category hierarchy.
- Tests for classification and retrieval behavior.

## Standards and licensing

Before importing or reproducing a complete published Dewey hierarchy, review
the applicable licensing and authorized access terms. The initial design
must not imply that a complete Dewey database has already been obtained or
implemented.
