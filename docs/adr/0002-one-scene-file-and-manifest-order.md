# ADR 0002: One YAML File per Scene, Manifest Owns Order

- Status: Accepted

## Context

A single large YAML file creates merge conflicts and makes scene-level changes difficult to review. Numbered filenames make ordering readable but cause renames whenever scenes move.

## Decision

Store each scene in its own YAML file. Store scene order only in `manual.yaml`. Scene and image basenames combine an immutable slug with a short UUID suffix.

## Consequences

- reordering changes only the manifest;
- title changes do not rename files;
- scenes can be reviewed and merged independently;
- the manifest is a small coordination hotspot;
- a project validator must detect orphaned or duplicate files.
