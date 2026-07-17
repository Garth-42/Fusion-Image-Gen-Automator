# 6. Test Strategy and Acceptance Criteria

## 6.1 Test pyramid

### Pure-Python unit tests

Run outside Fusion for:

- domain model creation;
- schema and semantic validation;
- UUID and filename rules;
- matrix and camera validation;
- manifest ordering;
- duplicate/delete behavior;
- atomic-write failure handling;
- path containment;
- message protocol parsing;
- application services using mocked ports.

### Contract tests

Validate:

- YAML examples against JSON schemas;
- serializer output against parser;
- palette request/response fixtures against protocol definitions;
- Fusion adapter DTOs against domain constructors.

### Fusion integration tests

Run inside Fusion against dedicated fixture assemblies for:

- attribute assignment and persistence;
- assembly traversal;
- camera round-trip;
- visibility round-trip;
- transform round-trip;
- opacity capability behavior;
- viewport export;
- state restoration after injected failures.

### Manual acceptance tests

Use a realistic documentation assembly and the actual palette.

## 6.2 Required fixture assemblies

### Fixture A - Simple local assembly

- root component;
- three child components;
- one hidden occurrence;
- one component at reduced opacity;
- one occurrence moved from assembled position.

### Fixture B - Nested assembly

- at least two nesting levels;
- repeated part names;
- occurrence proxies required in root context;
- parent hidden while child light bulb remains on.

### Fixture C - Repeated component

- same component definition instantiated at least twice;
- validates opacity limitations and identity uniqueness.

### Fixture D - Broken reference simulation

- scene created, then one occurrence removed or replaced;
- scene must report missing reference before mutation.

### Fixture E - Duplicate-ID simulation

- copy/paste or manually duplicate an FMSM attribute;
- apply/render must be blocked.

## 6.3 Unit-test cases

Minimum cases:

- valid manifest and scene parse;
- unknown schema version rejected;
- invalid UUID rejected;
- duplicate scene IDs rejected;
- duplicate scene files rejected;
- output path traversal rejected;
- absolute output path rejected;
- NaN/infinity rejected;
- matrix length other than sixteen rejected;
- eye equals target rejected;
- zero up vector rejected;
- invalid opacity rejected;
- title edit retains basename;
- reorder changes manifest order only;
- duplicate generates new UUID and basename;
- metadata-only update retains camera/state/output;
- atomic replacement preserves original on injected write failure;
- unsafe palette action rejected;
- mismatched request protocol rejected.

## 6.4 Fusion integration acceptance matrix

| ID | Scenario | Expected result |
|---|---|---|
| AT-001 | Initialize project on documentation assembly | Manifest, directories, local mapping, and document project ID are created |
| AT-002 | Create scene from current state | Scene YAML contains metadata, camera, all managed occurrences, opacities, transforms, and stable output paths |
| AT-003 | Close and reopen Fusion | Project resolves and scene list loads in manifest order |
| AT-004 | Change view, then load scene | Saved camera and assembly presentation are restored |
| AT-005 | Restore previous state | Pre-scene camera and assembly state return |
| AT-006 | Selectively update camera only | Only camera fields change in scene YAML |
| AT-007 | Edit title and description | Metadata changes; scene file and image basename remain unchanged |
| AT-008 | Duplicate scene | New UUID, files, and manifest entry; captured state copied; images absent until render |
| AT-009 | Reorder scene | Manifest order changes; filenames do not |
| AT-010 | Delete scene | Manifest, scene YAML, and existing assets are removed after confirmation |
| AT-011 | Render final image | Correct dimensions, PNG format, configured transparency, stable path |
| AT-012 | Force image export failure | Original Fusion state is restored and error is shown |
| AT-013 | Remove referenced occurrence | Load/render blocked before mutation with missing-reference error |
| AT-014 | Add new occurrence after capture | New occurrence is hidden on scene apply and warning is shown |
| AT-015 | Duplicate occurrence ID | Load/render blocked with duplicate-ID error |
| AT-016 | Project folder moved | User can relink local root without changing repository files |
| AT-017 | 200-scene project | Palette opens responsively; thumbnails load lazily |
| AT-018 | Dirty metadata and select another scene | Save/Discard/Cancel prompt prevents silent loss |
| AT-019 | Add-in unload with active scene | Restore is attempted and result is logged |
| AT-020 | Document mismatch | Clear warning; user cannot accidentally apply scene to unrelated design without explicit recovery action |

## 6.5 State-equivalence assertions

For camera and transforms, compare serialized numeric values within tolerance rather than object identity. Recommended initial tolerance: `1e-7` centimeters for matrix/camera coordinates, adjusted only if Fusion round-tripping demonstrates unavoidable noise.

Visibility and UUIDs require exact equality. Opacity tolerance may be `1e-6`.

## 6.6 Failure injection

Provide test seams to force failures after:

- transforms applied;
- opacity applied;
- visibility applied;
- camera applied;
- final PNG written;
- thumbnail write begun;
- temporary YAML written.

Every failure point must prove either state restoration or atomic-file preservation.

## 6.7 Regression artifacts

Keep under `tests/fixtures/`:

- canonical project manifest;
- canonical scenes;
- malformed YAML examples;
- message protocol fixtures;
- expected validation issue lists.

Generated PNGs should not be used as strict pixel-golden tests in the first deliverable because Fusion rendering can vary by platform and GPU. Validate dimensions, alpha presence, file readability, and basic nonempty pixel content instead.

## 6.8 Release gate

Release is blocked by:

- any state-restoration defect;
- any path-containment defect;
- partial YAML writes;
- silent identity ambiguity;
- scene order causing file renames;
- roadmap functionality displacing required MVP work.
