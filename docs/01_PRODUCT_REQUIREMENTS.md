# 1. Product Requirements

## 1.1 Product name

**Fusion Manual Scene Manager (FMSM)**

## 1.2 Problem statement

Assembly guides depend on carefully staged CAD images. Today those images are typically created as manual screenshots. When a part, assembly position, or camera view changes, the author must remember which images are affected and recreate them by hand. The first deliverable establishes repeatable, editable scene definitions inside Fusion so each image can be recreated from structured data.

## 1.3 Primary user

A mechanical or manufacturing engineer who:

- owns or understands the CAD assembly;
- authors assembly instructions;
- needs repeatable images with context and stable filenames;
- stores documentation sources in Git;
- is comfortable arranging an assembly in Fusion but should not need to edit YAML manually.

## 1.4 Product principle

FMSM stores both:

- **instructional intent:** title, description, purpose, and instruction text;
- **presentation state:** camera, visibility, opacity, transforms, and render settings.

The add-in does not attempt to infer assembly order or author instructions automatically.

## 1.5 Required operating model

The user must work in a **dedicated documentation assembly** that references production parts or assemblies. Scene loading may temporarily modify occurrence transforms, component opacity, and visibility. This isolation reduces the risk of modifying the production master.

The add-in must display this recommendation during project initialization and in the project settings view.

## 1.6 Functional requirements

### Project management

- **FR-001** Initialize a manual project in a user-selected local folder.
- **FR-002** Open an existing manual project.
- **FR-003** Associate the active Fusion documentation assembly with a project ID.
- **FR-004** Store the machine-specific project path only in local user settings.
- **FR-005** Validate that the active document matches the project's recorded source document when identifiers are available.

### Scene list and metadata

- **FR-010** Display scenes in manifest order.
- **FR-011** Show title, description excerpt, status, output state, and thumbnail.
- **FR-012** Create a scene from the current Fusion state.
- **FR-013** Edit title, description, purpose, instruction Markdown, and status.
- **FR-014** Duplicate a scene with a new immutable ID and new stable output filenames.
- **FR-015** Delete a scene only after confirmation.
- **FR-016** Reorder scenes by drag and drop without renaming files.
- **FR-017** Indicate unsaved metadata changes.

### Fusion state capture and restore

- **FR-020** Capture the current camera.
- **FR-021** Capture the light-bulb state of managed occurrences.
- **FR-022** Capture component opacity where the API supports replay.
- **FR-023** Capture root-context occurrence transforms as full matrices.
- **FR-024** Apply a scene to the active documentation assembly.
- **FR-025** Allow selective recapture of camera, visibility, opacity, and transforms.
- **FR-026** Capture a pre-scene session state before applying a scene.
- **FR-027** Restore the pre-scene session state on request.
- **FR-028** Restore the pre-render state after every render attempt, including failures.

### Stable identity

- **FR-030** Assign a UUID attribute to each managed occurrence.
- **FR-031** Assign a UUID attribute to each managed component required for opacity replay.
- **FR-032** Preserve friendly labels in YAML for human review, but resolve by UUID.
- **FR-033** Detect missing and duplicate IDs.
- **FR-034** Never silently repair duplicate IDs while applying or rendering a scene.

### Rendering

- **FR-040** Render a final PNG with stable filename.
- **FR-041** Render or refresh a thumbnail PNG.
- **FR-042** Support project defaults and per-scene width, height, transparency, and anti-aliasing.
- **FR-043** Use a path relative to project root for every asset.
- **FR-044** Return a clear success or failure result to the palette.

### Validation

- **FR-050** Validate project and scene YAML before use.
- **FR-051** Validate all referenced occurrence and component IDs.
- **FR-052** Warn about current assembly occurrences not listed in an older scene; they are hidden on apply.
- **FR-053** Detect invalid cameras, transforms, opacity values, and unsafe paths.
- **FR-054** Distinguish blocking errors from warnings.
- **FR-055** Provide actionable messages including scene title and affected component label.

## 1.7 Nonfunctional requirements

- **NFR-001 Reliability:** Scene application and rendering must use guaranteed cleanup paths.
- **NFR-002 Testability:** Most logic must be testable without Fusion.
- **NFR-003 Reviewability:** YAML must be deterministic and readable in Git diffs.
- **NFR-004 Safety:** The add-in never auto-saves a Fusion document.
- **NFR-005 Security:** The palette loads only local bundled content; YAML is loaded safely; writes cannot escape project root.
- **NFR-006 Performance:** A project with 200 scenes must open without eagerly embedding all thumbnails in one response.
- **NFR-007 Portability:** Version-controlled files contain no machine-specific absolute paths.
- **NFR-008 Compatibility:** The add-in avoids preview and undocumented Fusion APIs in production code.
- **NFR-009 Observability:** Errors are logged locally with operation, scene ID, and stack trace; user-facing messages omit irrelevant internals.
- **NFR-010 Recoverability:** Atomic file replacement prevents partial YAML writes.

## 1.8 Explicitly out of scope

- automatic determination of which scene is affected by a part revision;
- GitHub Actions, cloud execution, or Autodesk Platform Services automation;
- automatic update of external Fusion references;
- image comparison and approval workflow;
- callout anchors and projected annotation coordinates;
- document page layout or PDF generation;
- automatic BOM or fastener labels;
- scene branching, merge UI, multi-user locks, or remote database;
- capture of sketches, origins, analyses, construction geometry, or arbitrary viewport settings;
- deterministic per-occurrence opacity for repeated instances when Fusion exposes only shared component opacity.

## 1.9 Success criteria

The first deliverable succeeds when a user can create a ten-scene guide, close and reopen Fusion, reopen the manual project, load any scene, regenerate its image under the same filename, edit its instructional metadata, reorder it without file renames, and validate broken references after changing the assembly.
