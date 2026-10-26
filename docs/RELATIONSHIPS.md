# Eden Relationship Contract

## Purpose

Relationships connect knowledge records without collapsing them into one
record. Each relationship has its own stable identity, type, provenance,
creation timestamp, and optional confidence and evidence references.

## Supported types

- `supports`: the source supports the target.
- `contradicts`: the source contradicts the target.
- `derived_from`: the source was derived from the target.
- `supersedes`: the source supersedes the target.
- `part_of`: the source is part of the target.
- `depends_on`: the source depends on the target.
- `caused_by`: the source was caused by the target.
- `same_as`: both records refer to the same thing.
- `related_to`: the records are related without a more specific relation.

The source and target meanings are intentional. Directional relationships
must not be silently reversed.

`same_as` and `related_to` are symmetric. The other relationships are
directional in this contract.

## Validation

- Source and target identifiers must be non-empty.
- A record cannot be related to itself.
- Relationship types must use the declared enum.
- Provenance is required.
- Optional confidence must be numeric and between 0 and 1.
- Evidence identifiers must be non-empty strings.

## Provenance and evidence

Provenance explains where the relationship came from and why it was recorded.
Evidence identifiers point to supporting or challenging material. They are
not interchangeable.

## Scope

This contract defines an in-memory model only. It does not yet persist
relationships, verify that endpoint records exist, discover relationships
automatically, traverse the graph, or resolve contradictions.
Those capabilities require separate implementations and acceptance tests.
