# Agent Instructions

## Repository intent

This repository will contain a Fusion add-in, not a general web application. The palette is a local UI surface hosted inside Fusion. Fusion's HTML/JavaScript layer cannot call the Fusion API directly; it must send messages to the Python add-in.

## Scope guard

The only authorized product scope is the first deliverable in `README.md`. Treat `docs/07_ROADMAP.md` as non-executable context.

## Architecture rules

- `domain/` contains immutable or validation-oriented data models and no `adsk` imports.
- `application/` coordinates use cases through interfaces.
- `infrastructure/` handles YAML, local settings, logging, and filesystem safety.
- `fusion/` is the only package allowed to import `adsk`.
- `ui/` contains static palette assets and no business logic beyond presentation and message construction.
- Event handler objects must be retained for the life of the add-in.
- Fusion API calls must execute on the Fusion event/UI thread.
- Never use browser names or occurrence paths as persistent identity.
- Never store absolute local paths in version-controlled project files.

## Coding rules

- Prefer small modules and explicit dependency injection.
- Avoid syntax that is newer than necessary for Fusion's bundled Python runtime.
- Use dataclasses or simple classes; do not add a heavy framework.
- Use type hints where supported, but runtime correctness takes priority.
- All float serialization must reject NaN and infinity.
- Round persisted camera/matrix values consistently to avoid noisy Git diffs.
- Use `pathlib` and enforce project-root containment for every write.
- Use UTF-8, LF line endings, and deterministic key order.
- Use explicit error codes suitable for display in the palette.

## Testing rules

- Pure-Python tests must run without Fusion installed.
- Mock the Fusion adapter at the application-service layer.
- Keep Fusion integration tests deterministic and fixture-based.
- Every bug involving persistence receives a regression test.
- Every bug involving state restoration receives an integration-test case.

## Prohibited shortcuts

- No undocumented `executeTextCommand` calls.
- No automatic document saves.
- No direct YAML writes from UI event handlers.
- No giant single-file add-in.
- No use of names as IDs.
- No network dependency in the first deliverable.
- No implementation of roadmap features under the label of "future-proofing."
