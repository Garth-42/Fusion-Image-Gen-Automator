# ADR 0005: Local Palette with a Pure-Python Core

- Status: Accepted

## Context

The desired scene manager needs a rich persistent list and editor, while Fusion command dialogs are better suited to short modal tasks. Fusion APIs are unavailable in ordinary CI environments.

## Decision

Use a bundled HTML/CSS/JavaScript palette and a versioned JSON bridge to a Python add-in. Keep domain, validation, persistence, and application logic free of Fusion imports.

## Consequences

- UI can provide list, tabs, thumbnails, and drag reorder;
- most logic can be unit tested outside Fusion;
- message protocol requires validation and versioning;
- palette assets must remain local and secure;
- backend must retain Fusion event handlers.
