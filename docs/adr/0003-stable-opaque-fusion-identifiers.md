# ADR 0003: Stable Opaque Fusion Identifiers

- Status: Accepted

## Context

Fusion browser names, occurrence counters, paths, and part numbers can change or repeat. Scene replay needs identity that survives ordinary renaming.

## Decision

Assign UUID version 4 attributes to managed occurrences and components. Persist labels and part numbers only for readability and diagnostics.

## Consequences

- identity is independent of names;
- YAML diffs retain human context;
- copied attributes can create duplicates, requiring validation;
- dedicated assembly is modified when IDs are first assigned;
- IDs must never be silently regenerated during scene application.
