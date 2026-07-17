# 5. First-Deliverable Implementation Plan

This plan is intentionally limited to the first deliverable.

## 5.1 Milestone 0 - Skeleton and development harness

### Tasks

- Create Fusion Python add-in from the supported template.
- Add toolbar command to show the palette.
- Create bundled local palette with a basic request/response round trip.
- Establish package structure from `docs/02_SYSTEM_ARCHITECTURE.md`.
- Add standard logging and retained event-handler registry.
- Add ordinary CPython test runner configuration.

### Exit criteria

- Add-in loads and unloads without leaked toolbar controls.
- Palette opens, docks, closes, and exchanges a versioned ping message.
- Unit tests run without Fusion installed.

## 5.2 Milestone 1 - Domain models, schemas, and YAML store

### Tasks

- Implement project, scene, camera, occurrence state, component opacity, output, and validation models.
- Implement schema parsing and semantic validation.
- Vendor pure-Python YAML support.
- Implement deterministic serialization.
- Implement atomic writes and project-root containment.
- Implement project manifest and one-file-per-scene repository.
- Validate examples against JSON schemas in tests.

### Exit criteria

- Example files round-trip without semantic changes.
- Invalid matrices, paths, UUIDs, and schema versions fail with stable codes.
- Reordering changes only the manifest order.
- Metadata title change does not rename files.

## 5.3 Milestone 2 - Project initialization and association

### Tasks

- Implement local settings store.
- Implement project initialize/open use cases.
- Read/write project UUID on active Fusion document attributes.
- Record source document identity in manifest.
- Add project mismatch warnings.
- Create directory structure safely.

### Exit criteria

- Project can be reopened after Fusion restart on the same machine.
- Copying repository to another machine requires only reselecting its local root.
- No absolute path exists in `manual.yaml` or scene YAML.

## 5.4 Milestone 3 - Stable identity service

### Tasks

- Traverse all managed occurrences in root assembly context.
- Read and assign occurrence UUID attributes.
- Read and assign component UUID attributes needed for opacity.
- Build identity indexes.
- Detect missing and duplicate IDs.
- Add explicit Ensure IDs and Repair Duplicates commands.
- Preserve labels and part numbers for diagnostics.

### Exit criteria

- Capture never persists a name/path as identity.
- Duplicate IDs block scene apply/render.
- Missing IDs can be assigned through an explicit user action.
- Copy/paste collision fixture produces a clear diagnostic.

## 5.5 Milestone 4 - Fusion state capture and application

### Tasks

- Capture/apply camera using supported camera properties.
- Capture/apply occurrence light-bulb states.
- Capture/apply component opacity with capability checks.
- Capture/apply root-context transforms as Matrix3D values.
- Implement unlisted-occurrence hide-and-warn policy.
- Implement pre-scene session state capture and restore.
- Guard all state restoration with `finally` logic.

### Exit criteria

- Scene round-trip returns the fixture assembly to visually equivalent state.
- Restore returns the assembly to its pre-scene state.
- Apply validation performs no partial mutation on missing references.
- Supported nested occurrences are resolved in root context.

## 5.6 Milestone 5 - Scene application services and CRUD

### Tasks

- Create scene from current state.
- Edit metadata independently.
- Selectively recapture state sections.
- Duplicate with new ID and basename.
- Delete scene and assets safely.
- Reorder manifest.
- List scenes with output and validation summaries.

### Exit criteria

- All CRUD operations have unit tests through mocked ports.
- Duplicate never reuses IDs or output paths.
- Delete cannot escape project root.
- Metadata save never changes captured state fields.

## 5.7 Milestone 6 - Renderer and thumbnails

### Tasks

- Create image-export options from scene/project settings.
- Render final transparent anti-aliased PNG.
- Render thumbnail PNG.
- Implement guarded apply/render/restore flow.
- Add lazy thumbnail retrieval for palette.
- Add reveal-output and reveal-scene-file commands.

### Exit criteria

- Final image dimensions match scene configuration.
- Transparent background is present when requested.
- A forced export failure restores state.
- Render uses stable filenames after title edits and reorder.

## 5.8 Milestone 7 - Full palette UI

### Tasks

- Build project header, scene list, tabs, forms, status badges, and progress UI.
- Implement dirty metadata behavior.
- Implement drag reorder and keyboard alternatives.
- Implement create, load, restore, update capture, render, duplicate, delete, and validate actions.
- Escape all displayed user content.
- Add local CSS and icons only.

### Exit criteria

- Complete first-deliverable workflow is possible without manually editing YAML.
- Palette handles request timeout, backend error, and stale selection safely.
- 200-scene mock project remains responsive with lazy thumbnails.

## 5.9 Milestone 8 - Integration hardening and release candidate

### Tasks

- Build fixture documentation assemblies.
- Execute acceptance matrix on supported operating systems.
- Add crash/restart recovery notes.
- Add installation, upgrade, and uninstall documentation.
- Run static checks and test suite.
- Document known Fusion API limitations.

### Exit criteria

- All required acceptance tests pass.
- No open critical or high-severity defects.
- Known limitations are explicit and do not violate first-deliverable acceptance criteria.

## 5.10 Suggested pull-request slices

1. Add-in/palette skeleton
2. domain and schema package
3. YAML and settings persistence
4. identity service
5. camera and visibility adapter
6. transforms and opacity adapter
7. state guard
8. scene CRUD services
9. renderer
10. palette scene list and content editor
11. palette capture/output/validation actions
12. fixtures and release documentation

Each pull request should remain independently testable and avoid roadmap features.

## 5.11 Definition of done checklist

- [ ] Project initialize/open works.
- [ ] Scene create/edit/duplicate/delete/reorder works.
- [ ] Camera capture/apply works.
- [ ] Visibility capture/apply works.
- [ ] Supported opacity capture/apply works with limitations reported.
- [ ] Transform capture/apply works for supported fixture occurrences.
- [ ] Pre-scene and pre-render restoration works.
- [ ] Final and thumbnail PNG generation works.
- [ ] Stable IDs and filenames persist.
- [ ] YAML is valid, deterministic, and atomic.
- [ ] Validation messages are actionable.
- [ ] Pure-Python tests pass.
- [ ] Fusion integration and acceptance tests pass.
- [ ] Roadmap functionality is not present.
