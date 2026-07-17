# ADR 0001: Use a Dedicated Documentation Assembly

- Status: Accepted
- Scope: First deliverable

## Context

Loading a scene may change occurrence transforms, visibility, opacity, and camera. These operations can mark a Fusion design modified and may interact with joints.

## Decision

FMSM is designed around a dedicated documentation assembly that references production components. The add-in never auto-saves it and captures/restores temporary state.

## Consequences

### Positive

- protects production master geometry;
- permits authored exploded positions;
- isolates manual-specific attributes;
- provides a stable top-level assembly for scene IDs.

### Negative

- requires users to maintain one additional Fusion document;
- referenced parts must still be updated intentionally;
- a crash may leave the documentation assembly visually altered until reopened or restored.

## Rejected alternatives

- Mutate production assembly directly: unacceptable risk.
- Implement custom-graphics-only scenes in MVP: too much scope and does not cover all display behavior.
- Clone the assembly automatically: cloud/data-management complexity is outside MVP.
