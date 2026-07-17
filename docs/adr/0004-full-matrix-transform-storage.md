# ADR 0004: Store Full Transformation Matrices

- Status: Accepted

## Context

Exploded positions can include arbitrary rotations and translations. Euler angles introduce ordering ambiguity and numeric drift.

## Decision

Persist the complete sixteen-value Matrix3D representation in centimeters and apply it in root assembly context.

## Consequences

- exact round-trip is simpler;
- YAML is less friendly for hand editing;
- the palette is the intended authoring surface;
- semantic validation must check length and finite values;
- later tools may add derived translation/rotation summaries without replacing the matrix.
