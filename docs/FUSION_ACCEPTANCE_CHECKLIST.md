# Fusion Acceptance Checklist — Release Candidate

Use this checklist for the fixture-based Fusion pass before tagging a first-deliverable release candidate. Run every case from a fresh Fusion session with the current `addin/FusionManualSceneManager` bundle installed.

## 1. Fixture setup

Prepare dedicated documentation assemblies. Do not use a production master assembly.

| Fixture | Required contents | Acceptance focus |
|---|---|---|
| A: Simple local assembly | Root component, three child components, one hidden occurrence, one reduced-opacity component, one moved occurrence | Project setup, capture, render, restore |
| B: Nested assembly | At least two nesting levels, repeated display names, parent and child visibility differences | Root-context occurrence identity and transform replay |
| C: Repeated component | Same component definition instantiated at least twice | Component UUID uniqueness and opacity limitations |
| D: Broken reference | Scene captured before one occurrence is removed or replaced | Reference validation blocks mutation |
| E: Duplicate ID | Copy/pasted or manually duplicated FMSM UUID attribute | Duplicate detection blocks apply/render |

## 2. Project and identity gate

1. Start Fusion and open Fixture A.
2. Run **Fusion Manual Scene Manager** from **Utilities > Add-Ins > Scripts and Add-Ins**.
3. Confirm the palette reaches `Add-in connected.`.
4. Initialize a project in an empty Git working tree.
5. Press **Ensure IDs**.
6. Press **Refresh** and confirm the Stable IDs section reports unique occurrence and component IDs.
7. Stop and rerun the add-in; the project should reopen without reselecting its root.

Expected result: `manual.yaml`, `scenes/`, `assets/generated/`, and `assets/thumbnails/` exist; the active Fusion document has the project association; no absolute path is written to repository YAML.

## 3. Scene authoring gate

1. Set Fixture A to a distinctive camera angle.
2. Hide one occurrence, lower one component opacity, and move one managed occurrence.
3. Enter a scene title and press **Create Scene from Current State**.
4. Select **Edit** for the new scene.
5. Update title, status, description, purpose, and Markdown instructions; press **Save Metadata**.
6. Create a second scene and use **Move Up** / **Move Down**.
7. Press **Duplicate** on one scene.
8. Press **Delete** on the duplicate.

Expected result: scene YAML is created under `scenes/`; metadata edits do not rename the file or output basename; reordering changes only `manual.yaml`; deletion removes the scene YAML and any generated assets without touching files outside the project root.

## 4. State replay and restore gate

1. With Fixture A open, press **Capture Current State**.
2. Change camera, visibility, opacity, and transforms.
3. Press **Apply Captured State**.
4. Press **Restore Previous State**.
5. Repeat using Fixture B.

Expected result: applying a captured state restores the captured camera and assembly presentation; explicit restore returns to the pre-apply state. Nested occurrences replay in root context.

## 5. Render gate

1. Select a persisted scene and press **Render**.
2. Open the generated PNG and thumbnail from `assets/generated/` and `assets/thumbnails/`.
3. Confirm dimensions match the scene output settings.
4. Confirm the Fusion assembly returns to its pre-render state after render completes.
5. Repeat after intentionally making the output folder read-only or otherwise forcing export failure.

Expected result: successful render writes stable final and thumbnail PNG filenames; forced export failure reports `RENDER_FAILED`; Fusion state is restored after both success and failure.

## 6. Validation gate

1. Open Fixture D and render/apply a scene that references the removed occurrence.
2. Open Fixture E and press **Stable IDs > Repair Duplicate IDs** only after first confirming duplicate diagnostics.
3. Re-run scene render/apply after duplicate repair.

Expected result: broken references and duplicate IDs block mutation before any partial apply. Repairing duplicate IDs is explicit and visible to the user.

## 7. Palette robustness gate

1. Open a project with at least 200 scene entries.
2. Refresh the palette, edit metadata, reorder scenes, and render one scene.
3. Stop and rerun the add-in.
4. Exercise a stale installed-copy failure by reinstalling the bundle and restarting Fusion.

Expected result: the palette remains responsive, all displayed user text is escaped, one request at a time is enforced, and connection failures produce the documented troubleshooting states.

## 8. Release blocker audit

A release candidate is blocked by any of the following:

- state restoration fails after apply or render;
- YAML write escapes the project root or partially overwrites a file;
- duplicate/missing stable IDs are silent;
- scene reorder changes scene filenames;
- render output dimensions are wrong;
- a roadmap feature is introduced instead of first-deliverable behavior;
- the palette leaves the user without an actionable error message.
