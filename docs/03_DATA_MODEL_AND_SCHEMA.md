# 3. Data Model and Schema

The machine-readable definitions are in `schemas/manual-project.schema.json` and `schemas/scene.schema.json`. This document explains the design choices.

## 3.1 Repository structure

```text
manual.yaml
scenes/
  install-left-din-rail__78b36cd7.yaml
  install-right-din-rail__9a3dd5f1.yaml
assets/
  generated/
    install-left-din-rail__78b36cd7.png
  thumbnails/
    install-left-din-rail__78b36cd7.png
```

Scene order exists only in `manual.yaml`. Reordering must not rename scene or image files.

## 3.2 Project manifest

```yaml
schema_version: 1
project:
  id: 0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db
  title: Printer E-Box Assembly Guide
  source_document:
    data_file_id: urn:adsk.wipprod:dm.lineage:example
    name: Printer E-Box Documentation Assembly
    role: documentation_assembly
  render_defaults:
    width_px: 2400
    height_px: 1600
    transparent_background: true
    anti_alias: true
  scenes:
    - scene_id: 78b36cd7-532e-4d82-b8d7-b04ccbfa73ae
      file: scenes/install-left-din-rail__78b36cd7.yaml
```

`data_file_id` may be null for an unsaved or unavailable document, but the UI should warn that document matching is weaker.

## 3.3 Scene metadata

Every scene contains:

- immutable UUID;
- immutable slug unless explicitly renamed through a dedicated future operation;
- editable title;
- editable description;
- editable purpose;
- editable Markdown instruction text;
- status (`draft`, `review`, `approved`, or `obsolete`);
- optional tags.

The slug is generated at creation and is not automatically changed when the title changes. This preserves stable filenames.

## 3.4 Source snapshot

The scene records source context for diagnostics, not identity resolution:

```yaml
source:
  document_data_file_id: urn:...
  document_name: Printer E-Box Documentation Assembly
  captured_at_utc: 2026-07-17T13:00:00Z
  fusion_version: 2.x
```

The first deliverable does not use component revision IDs to decide whether a scene is stale. That belongs to Phase 2.

## 3.5 Camera serialization

Persist:

- camera type;
- eye point;
- target point;
- up vector;
- orthographic width and height, or perspective angle;
- `is_fit_view: false`.

Coordinates and extents are stored in centimeters to match Fusion API geometry units.

```yaml
camera:
  type: orthographic
  eye_cm: [41.26, -31.82, 27.74]
  target_cm: [0.0, 0.0, 3.2]
  up_vector: [0.0, 0.0, 1.0]
  extents_cm:
    width: 54.0
    height: 36.0
  perspective_angle_rad: null
```

Validation rejects:

- non-finite values;
- coincident eye and target;
- zero-length up vector;
- nonpositive orthographic extents;
- missing perspective angle for perspective cameras.

## 3.6 Occurrence visibility and transforms

Each scene contains a complete explicit list of managed occurrences at capture time.

```yaml
occurrences:
  - occurrence_id: 5ceae402-b6b4-4a27-88db-2a3b6b27d54f
    label: Left DIN Rail:1
    part_number: RAIL-DIN-200
    visible: true
    transform_matrix_cm:
      - 1.0
      - 0.0
      - 0.0
      - 0.0
      - 0.0
      - 1.0
      - 0.0
      - 0.0
      - 0.0
      - 0.0
      - 1.0
      - 0.0
      - 0.0
      - 0.0
      - 3.5
      - 1.0
```

The matrix contains sixteen row-major values. Persisting the full matrix avoids lossy Euler-angle decomposition and accurately recreates the authored position.

When a current occurrence is absent from an older scene, the apply policy is:

- hide it;
- report warning `UNLISTED_OCCURRENCE_HIDDEN`;
- do not modify the scene file automatically.

## 3.7 Component opacity

Opacity is recorded separately because Fusion exposes opacity primarily through components or bodies rather than a simple occurrence-level setter.

```yaml
components:
  - component_id: 7e4225a8-9233-48f2-8a75-535659a21cd0
    label: Previously Installed Components
    opacity: 0.25
```

Validation must detect conflicting requirements when multiple occurrences share a component and the desired visual result cannot be replayed independently with supported APIs. The first deliverable reports a warning or blocking error according to actual replay capability; it does not implement custom-graphics ghosting.

## 3.8 Output settings

```yaml
output:
  image_file: assets/generated/install-left-din-rail__78b36cd7.png
  thumbnail_file: assets/thumbnails/install-left-din-rail__78b36cd7.png
  width_px: 2400
  height_px: 1600
  thumbnail_width_px: 480
  thumbnail_height_px: 320
  transparent_background: true
  anti_alias: true
```

All paths are POSIX-style project-relative paths even on Windows. The storage layer converts them to native paths after containment checks.

## 3.9 Stable filename rules

At scene creation:

1. slugify title to lowercase ASCII words separated by hyphens;
2. use `scene` when no usable characters remain;
3. append `__` and first eight hexadecimal characters of scene UUID;
4. retain the resulting basename for the life of the scene.

Example:

```text
Install Left DIN Rail
→ install-left-din-rail__78b36cd7
```

Title edits and scene reorder do not rename this basename.

## 3.10 Deterministic YAML rules

- UTF-8 and LF endings;
- two-space indentation;
- block style, never flow style for mappings;
- keys emitted in schema order;
- no Python object tags;
- multiline instruction text emitted as a literal block when practical;
- finite floats only;
- floats rounded consistently, recommended nine decimal places;
- final newline required;
- safe load and safe dump only.

## 3.11 Atomic-write algorithm

1. Serialize and validate in memory.
2. Write to a temporary file in the destination directory.
3. Flush and fsync the temporary file when supported.
4. Parse the temporary file again.
5. Replace the destination atomically.
6. Leave the original file untouched on any failure.

## 3.12 Schema-version policy

The first deliverable reads only `schema_version: 1`.

- Higher versions fail with `SCHEMA_VERSION_UNSUPPORTED`.
- Missing versions fail with `SCHEMA_VERSION_MISSING`.
- Future migrations must be explicit pure functions from one version to the next.
- The first deliverable does not write migration code for hypothetical versions.

## 3.13 Deletion semantics

Deleting a scene removes:

- its manifest entry;
- its YAML file;
- its generated PNG;
- its thumbnail PNG.

Deletion occurs only after confirmation and project-root containment checks. Missing image files are warnings, not failures.
