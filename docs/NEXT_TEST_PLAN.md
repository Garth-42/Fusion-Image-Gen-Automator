# Next Test Plan for Fusion Manual Scene Manager

This checklist captures the near-term tests that should be run before treating the current add-in as a first-deliverable release candidate. It focuses on the local interactive workflow: project association, stable IDs, scene capture/load/update, preview, rendering, validation, and state restoration.

## 1. Automated tests outside Fusion

Run these from the repository root after every code change:

```bash
python -m pytest
```

Targeted checks for recent workflow areas:

```bash
python -m pytest tests/unit/test_preview_service.py
python -m pytest tests/unit/test_render_service.py
python -m pytest tests/unit/test_scene_service.py
python -m pytest tests/unit/test_project_service.py
python -m pytest tests/unit/test_fusion_adapter_references.py
python -m pytest tests/unit/test_palette_document.py tests/unit/test_protocol.py
```

Also run a whitespace/diff sanity check before committing:

```bash
git diff --check
```

## 2. Required Fusion fixture assemblies

Create and keep dedicated test assemblies. Do not use production assemblies for acceptance testing.

| Fixture | Contents | Main purpose |
| --- | --- | --- |
| A: Simple local assembly | Root component, three child components, one hidden occurrence, one reduced-opacity component, one moved occurrence | Basic project, capture, render, restore |
| B: Nested assembly | At least two nesting levels, repeated display names, parent/child visibility differences | Root-context occurrence identity and transform replay |
| C: Repeated component | Same component definition instantiated at least twice | Component ID de-duplication and opacity behavior |
| D: Broken reference | Scene captured before one occurrence is removed/replaced | Missing-reference validation before mutation |
| E: Duplicate ID | Copy/pasted or manually duplicated FMSM UUID attributes | Duplicate ID detection and repair workflow |

## 3. Project and association tests in Fusion

1. Start Fusion from a fresh session.
2. Open Fixture A.
3. Run **Fusion Manual Scene Manager** from **Utilities > Add-Ins > Scripts and Add-Ins**.
4. Confirm the palette reaches `Add-in connected.`.
5. Initialize a project in an empty Git working tree.
6. Confirm `manual.yaml`, `scenes/`, `assets/generated/`, and `assets/thumbnails/` are created.
7. Press **Ensure IDs**.
8. Press **Refresh** and confirm Stable IDs reports unique occurrence/component IDs.
9. Stop and rerun the add-in with the same Fusion document open.
10. Confirm the project automatically resolves and the scene list loads without reselecting the root.
11. Move or hide the local settings entry, then confirm **Open Project** can relink the folder.
12. Try initializing when the document already has an association, cancel replacement, and confirm no new `manual.yaml` is written.
13. Repeat initialization and accept replacement, then confirm the document points to the new project ID.

Expected result: project association is recoverable, no absolute path is written into repository YAML, and accidental reassociation is blocked unless explicitly confirmed.

## 4. Stable ID tests in Fusion

1. On Fixture A, press **Ensure IDs** and confirm missing IDs become valid UUIDs.
2. Press **Ensure IDs** again and confirm it does not churn existing valid IDs.
3. On Fixture E, introduce duplicate occurrence and component UUID attributes.
4. Confirm duplicate IDs are reported before scene apply/render.
5. Press **Repair Duplicate IDs** only after confirming duplicate diagnostics.
6. Confirm repair changes only the duplicate entities and leaves unique entities stable.

Expected result: duplicate and missing stable IDs are visible and actionable; scene apply/render does not silently proceed with identity ambiguity.

## 5. Scene authoring tests in Fusion

1. Set Fixture A to a distinctive camera angle.
2. Hide one occurrence, reduce one component opacity, and move one managed occurrence.
3. Enter a scene title and press **Create Scene from Current State**.
4. Confirm a scene YAML file is created under `scenes/`.
5. Click **Edit** and update title, status, description, purpose, and Markdown instructions.
6. Press **Save Metadata**.
7. Confirm metadata changes do not rename the scene file or output basename.
8. Create a second scene.
9. Use **Move Up** and **Move Down**.
10. Duplicate a scene and confirm the copy receives a new scene ID and output paths.
11. Delete the duplicate and confirm its scene YAML and generated assets are removed without touching files outside the project root.

Expected result: scene CRUD preserves stable filenames and updates only the intended YAML fields.

## 6. Load scene and restore tests in Fusion

1. Create at least two scenes with obviously different cameras and visibility states.
2. Change the live Fusion viewport away from both scenes.
3. Click **Load Scene** for the first scene.
4. Confirm Fusion changes to that scene's saved camera and assembly presentation.
5. Click **Restore Previous State**.
6. Confirm Fusion returns to the pre-load camera and assembly presentation.
7. Repeat with the second scene.
8. Repeat with Fixture B to verify nested occurrence transforms replay correctly.

Expected result: **Load Scene** previews persisted scene YAML, while **Restore Previous State** returns to the state that existed before loading.

## 7. Update graphics tests in Fusion

1. Create a scene from Fixture A.
2. Edit and save metadata/instructions.
3. Move the Fusion camera and change visibility/opacity/transforms.
4. Click **Update Graphics from Current State** for the selected scene.
5. Confirm the scene file keeps the same metadata and output paths.
6. Render the scene and confirm the generated image reflects the updated graphics.

Expected result: graphics are recaptured without changing scene metadata, scene filename, or output filenames.

## 8. Render tests in Fusion

1. Select a persisted scene and click **Render**.
2. Confirm final PNG is written under `assets/generated/`.
3. Confirm thumbnail PNG is written under `assets/thumbnails/`.
4. Open both images and confirm dimensions match scene output settings.
5. Confirm Fusion returns to its pre-render state after render completes.
6. Force image export failure by making an output folder read-only or otherwise unavailable.
7. Confirm `RENDER_FAILED` is shown and Fusion state is restored.
8. Click **Render All Scenes** and confirm every scene renders in manifest order.
9. Confirm render-all does not leave Fusion in the final scene state.

Expected result: render writes stable assets, failures are visible, and Fusion state restoration is reliable after both success and failure.

## 9. Preview summary tests in Fusion

1. Open a project with at least one scene that has already been rendered in a previous session.
2. Click **Preview Summary**.
3. Confirm the preview panel opens inside the palette.
4. Confirm each scene displays the rendered image first, before description/purpose/instructions.
5. Confirm scene title, status, scene ID, description, purpose, Markdown instructions, generated image path, and thumbnail path are present.
6. Close and reopen the preview.
7. Add another scene, render it, refresh, and confirm the preview includes it.
8. Test a scene without a generated image and confirm the preview still renders the text context without failing.

Expected result: preview is useful for quick review, shows previously rendered images when available, and does not depend on popup windows or external files.

## 10. Reference validation tests in Fusion

1. Use Fixture D to create a scene, then remove or replace one referenced occurrence.
2. Try **Load Scene**, **Render**, and **Render All Scenes**.
3. Confirm missing occurrence references block mutation before any partial apply.
4. Add a new occurrence after scene capture.
5. Load/render the older scene and confirm unlisted occurrences are hidden with warnings according to current apply policy.
6. Use Fixture C to verify repeated occurrences of the same component do not produce false `DUPLICATE_COMPONENT_ID` errors.
7. Verify truly distinct components with the same component UUID still produce duplicate diagnostics.

Expected result: broken references and true duplicate IDs block apply/render; repeated component instances are handled without false duplicate errors.

## 11. Palette robustness tests in Fusion

1. Open a project with at least 200 scene entries.
2. Refresh the palette.
3. Edit metadata.
4. Reorder scenes.
5. Load one scene.
6. Render one scene.
7. Render all scenes if practical for the fixture size.
8. Open and close the preview summary.
9. Stop and rerun the add-in.
10. Reinstall or replace the add-in bundle and restart Fusion to catch stale installed-copy behavior.

Expected result: the palette remains responsive, one request at a time is enforced, displayed text is escaped, and connection failures show actionable messages.

## 12. Release blocker audit

Do not tag a first-deliverable release candidate if any of these occur:

- state restoration fails after load, apply, render, or render-all;
- YAML writes escape the project root;
- YAML writes partially overwrite a file after failure;
- duplicate or missing stable IDs are silent;
- scene reorder changes scene filenames;
- metadata edits rename output assets unexpectedly;
- render output dimensions are wrong;
- preview fails to render for a valid project;
- roadmap features displace local first-deliverable behavior;
- the palette leaves the user without an actionable error message.

## 13. Bugs discovered during acceptance

For every bug found in Fusion acceptance:

1. Record the fixture, exact action sequence, expected result, and actual result.
2. Add or update a pure-Python regression test when the behavior can be isolated outside Fusion.
3. Add a Fusion acceptance note when live API behavior cannot be represented in CPython.
4. Re-run the targeted tests and full `python -m pytest` suite.
