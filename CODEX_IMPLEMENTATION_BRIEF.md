# Codex Implementation Brief

## Mission

Implement the first deliverable of Fusion Manual Scene Manager exactly as defined by this architecture package. Produce a working Fusion Python add-in with a dockable scene-authoring palette and a testable pure-Python core.

## Highest-priority constraints

1. **Implement only the first deliverable.** Roadmap sections are context, not authorization to expand scope.
2. **Use a dedicated documentation assembly.** Do not assume the active design is safe to mutate.
3. **Keep Fusion API calls behind adapters.** Domain and persistence logic must run under ordinary CPython for unit testing.
4. **Use one YAML file per scene plus a project manifest.** The manifest is the only source of scene order.
5. **Use stable opaque UUIDs stored as Fusion attributes.** Names and browser paths are labels, not identity.
6. **Write files atomically.** Never partially overwrite a project or scene YAML file.
7. **Use `yaml.safe_load` and deterministic safe dumping.** Do not deserialize arbitrary Python objects.
8. **Do not use undocumented Fusion text commands.** Use the supported API only.
9. **Restore state in `finally` blocks.** A rendering failure must not strand the assembly in an altered scene.
10. **Do not auto-save the Fusion document.** The user controls saving.

## Implementation sequence

Implement in this order:

1. Repository/add-in skeleton and test harness.
2. Domain models, schema validation, and YAML store.
3. Project initialization and local project-path association.
4. Stable occurrence/component identity service.
5. Camera and assembly-state capture/apply adapters.
6. Session state guard and restore behavior.
7. PNG renderer and thumbnails.
8. Palette UI and JSON message protocol.
9. CRUD, reorder, render, and validation workflows.
10. Integration fixtures, acceptance tests, packaging notes.

Do not begin dependency tracking, CI automation, callouts, publishing integration, or image diffing.

## Deliverables expected from implementation

- Fusion add-in source and manifest
- vendored YAML dependency or documented packaging step
- pure-Python unit tests
- Fusion integration test checklist and fixture instructions
- sample project generated from `examples/`
- installation and usage instructions
- concise known-limitations document

## Required quality gates

- No Fusion imports in domain, schema, and YAML-store modules.
- No absolute project path stored in repository YAML or cloud document metadata.
- All palette messages are schema-checked before dispatch.
- All output paths are normalized and verified to remain inside the project root.
- Duplicate Fusion IDs are blocking validation errors.
- Missing scene references are blocking validation errors.
- A failed render restores camera, visibility, opacity, and transforms.
- Reordering scenes does not rename scene or image files.
- Editing a title does not change a scene ID or output filename.
- Unknown YAML fields are preserved only if explicitly supported; otherwise fail clearly rather than silently discarding data.

## Default technical choices

Unless implementation evidence requires a change:

- Language: Python add-in using the bundled Fusion Python runtime
- UI: Fusion palette backed by local HTML/CSS/JavaScript
- Persistence: YAML with vendored pure-Python PyYAML
- IDs: UUID version 4 strings
- Images: PNG, transparent background, anti-aliased
- Final image default: 2400 x 1600
- Thumbnail default: 480 x 320
- Units in persisted geometry: centimeters, matching Fusion API geometry units
- Matrix representation: sixteen row-major numeric values
- Project settings: local user settings map `project_id` to repository path

## Change control

If an API limitation makes a requirement infeasible, document the limitation, isolate it behind an adapter, add a failing or skipped integration test, and implement the smallest supported fallback. Do not silently reduce the requirement or introduce an unrelated platform.
