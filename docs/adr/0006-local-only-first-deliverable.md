# ADR 0006: Local Interactive First Deliverable

- Status: Accepted

## Context

Cloud rendering, CI, stale detection, and PDF publishing are valuable, but each introduces credentials, distributed execution, revision semantics, and additional failure modes.

## Decision

The first deliverable is a local interactive Fusion add-in. It stores Git-friendly sources and generated images but does not automate Git, cloud rendering, or publishing.

## Consequences

- faster validation of the authoring concept;
- no credential or hosted-service requirements;
- users trigger renders manually;
- architecture keeps application services separable for a future headless entry point;
- roadmap work cannot be used to justify MVP scope expansion.
