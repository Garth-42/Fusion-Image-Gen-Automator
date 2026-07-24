# PR #27 — Computer-Use Verification Plan (Fusion)

A live-Fusion test plan for an agent driving the machine through **Claude computer
use** (screenshots + mouse/keyboard, with a terminal for file and image checks).
It verifies the fixes in PR #27 and the items those fixes left for in-Fusion
confirmation. The pure-Python suite already passes; this plan covers only what
requires a running Fusion session.

## What PR #27 changed (map of coverage)

| Fix | Commit | Layer | Verified by |
|---|---|---|---|
| Silent render failure now raises `RENDER_FAILED` | `5f4bec5` | render service + adapter | §2 |
| Palette blank-on-open / stale-after-document-switch repaint | `5f4bec5` | `ui/palette.html` | §1 |
| "Checking stable IDs…" feedback clears when the check settles | `5f4bec5` | `ui/palette.html` | §1.4 |
| Nested-occurrence transforms replay via `transformOccurrences` batch | `556a04f` | adapter | §3 |
| Per-occurrence opacity via assembly-context proxy | `556a04f` | schema + validation + adapter | §4 |

Two API-behavior assumptions the seam tests could not exercise are the crux and
must be confirmed here:

- **A-1** `rootComponent.transformOccurrences(occs, mats, ignoreJoints=True)` applies each matrix as the **absolute** root-context transform → §3.
- **A-2** `component.createForAssemblyContext(occurrence).opacity` sets a **per-instance** override → §4.

## How to execute and verify (computer-use conventions)

- **Screenshots are the primary evidence.** Capture the palette and the viewport
  before and after each action. Zoom the palette panel if text is too small to read.
- **Use the terminal for anything a screenshot cannot prove**: file existence,
  image dimensions, pixel diffs, YAML contents, making a folder read-only.
- **Never let the add-in save the document for you.** It never auto-saves by
  design; save the Fusion document yourself only where a step says to.
- **Handle native dialogs** (folder pickers, confirm boxes, message boxes) by
  screenshot-then-click; they block the palette until dismissed.
- **Do not use the collapse/expand or minimize/maximize nudge** anywhere in §1 —
  the whole point is that the palette must paint without it.
- Capture the add-in version shown in **Utilities → Add-Ins → Scripts and
  Add-Ins** at the start so results are attributable to the PR #27 bundle.

### Terminal recipes (adapt paths / OS)

```bash
# Image dimensions
python3 -c "from PIL import Image; print(Image.open('assets/generated/NAME.png').size)"
# Pixel diff: getbbox() is None when identical, a box when they differ
python3 -c "from PIL import Image, ImageChops as C; a=Image.open('A.png').convert('RGB'); b=Image.open('B.png').convert('RGB'); print(C.difference(a,b).getbbox())" 
# Read a scene's assembly_state opacity placement
python3 -c "import yaml,glob; d=yaml.safe_load(open(sorted(glob.glob('scenes/*.yaml'))[-1])); a=d['assembly_state']; print('occ opacity:',[o.get('opacity') for o in a['occurrences']]); print('comp keys:',[sorted(c) for c in a['components']])"
# Force an export failure (macOS/Linux); restore afterward
chmod -R a-w assets/generated        # make read-only
chmod -R u+w assets/generated        # restore
# Windows equivalent: icacls assets\generated /deny "%USERNAME%":(W)   ... /remove:d "%USERNAME%"
```

## Preconditions

1. Fusion installed; the PR #27 `addin/FusionManualSceneManager` bundle installed and run.
2. A Git working tree for the manual project (the add-in does not run `git init`).
3. Fixtures A–E from `docs/FUSION_ACCEPTANCE_CHECKLIST.md §1`, plus the extras below.
4. Palette reaches **`Add-in connected.`** before starting any section.

### Extra fixtures this plan needs

- **B-nested**: Fixture B with at least two nesting levels and a child clearly
  offset from its parent (so corruption is visible). Note one child's position
  relative to its parent before capture.
- **A-opacity**: on Fixture A, set exactly one occurrence's opacity to ~35% via
  right-click **Opacity** in the browser (this creates the per-instance override
  the fix targets).
- **C-repeated**: Fixture C (same component instantiated ≥2×); you will give the
  two instances different opacities in §4.2.
- **legacy-scene**: one scene YAML in the pre-PR shape — `assembly_state.components[]`
  carries `opacity`, and `assembly_state.occurrences[]` has **no** `opacity` key.
  Hand-craft it, or copy a scene authored before PR #27.

---

## §1 Palette rendering and responsiveness — verifies `5f4bec5`

### CU-1.1 Blank-on-open paints without a nudge
1. Ensure the add-in is stopped and the palette is closed.
2. Run the add-in from Scripts and Add-Ins. Screenshot the palette **immediately**
   and again ~2 s later, touching nothing.
- **PASS**: the palette shows its full content (heading, "Connecting…"/"Add-in
  connected.", Project section, buttons) with no manual nudge.
- **FAIL**: it shows only the title bar and a fragment (e.g. just "Fusion") and
  stays blank until resized. *(This was the reported failure.)*

### CU-1.2 Stop/rerun paints without a nudge
1. Stop the add-in, then run it again. Screenshot immediately.
- **PASS**: fully painted, as CU-1.1. **FAIL**: blank/partial until nudged.

### CU-1.3 Document switch updates on Refresh alone
1. With the add-in running against **Fixture A**, note the palette's `Document:` line.
2. Open a different document (or a new Untitled), make it active.
3. Click **Refresh** in the palette. Screenshot. Do **not** collapse/expand.
- **PASS**: the `Document:` line now names the newly active document.
- **FAIL**: it still shows the previous document until a collapse/expand nudge.

### CU-1.4 "Checking stable IDs…" feedback clears
1. From CU-1.3 (a document is open), click **Refresh**.
2. Watch the project feedback line while the Stable IDs section populates; screenshot after it settles.
- **PASS**: the Stable IDs section shows its result (e.g. "N occurrence(s) and M
  component(s) have unique stable IDs") and the feedback line is **empty**.
- **FAIL**: the feedback line still reads "Checking stable IDs…" after the check completed.

---

## §2 Render gate — silent failure now surfaced — verifies `5f4bec5`

### CU-2.1 Successful render (regression)
1. Select a persisted Fixture A scene; click **Render**.
2. Terminal: check `assets/generated/<name>.png` = **2400×1600** and
   `assets/thumbnails/<name>.png` = **480×320**.
- **PASS**: both files exist at those dimensions; palette shows "Rendered … and …";
  the assembly returns to its pre-render pose.

### CU-2.2 Read-only output folder → `RENDER_FAILED` (not silent)
1. Terminal: make the generated folder read-only (`chmod -R a-w assets/generated`).
2. Click **Render** on a scene. Screenshot the palette feedback line.
- **PASS**: feedback shows **`Error (RENDER_FAILED):`** with a message about no
  image being written / folder not writable.
- **FAIL**: any "Rendered …" success text, or no message at all (the original silent failure).
3. Terminal: restore write (`chmod -R u+w assets/generated`).

### CU-2.3 State restored after the forced failure
1. Immediately after CU-2.2, screenshot the viewport.
- **PASS**: the assembly is back in its pre-render pose (camera, visibility,
  transforms, opacity) despite the failure.

---

## §3 Nested-occurrence transforms — Fixture B — verifies `556a04f` + **A-1**

### CU-3.1 Apply Captured State keeps nested children in place
1. Open **B-nested**. Frame a clear view; screenshot the viewport (this is the reference pose).
2. Click **Capture Current State**.
3. Move the parent occurrence, then move a nested child, and change the camera.
4. Click **Apply Captured State**. Screenshot the viewport.
- **PASS**: the assembly matches the reference-pose screenshot — every nested child
  sits at its original offset from its parent; nothing is detached or floating.
- **FAIL**: the parent returns correctly but nested children are displaced (offset
  by roughly the parent's move). *(This is the exact Fixture B corruption.)*
- Optional quantitative check: before capture, use **Inspect → Measure** for the
  distance between a parent vertex and a child vertex; repeat after Apply — the
  distance must match.

### CU-3.2 Restore Previous State (restore path also fixed)
1. After CU-3.1, click **Restore Previous State**. Screenshot.
- **PASS**: the assembly returns to the *modified* pose from step 3, nested children
  intact (the same batch-transform path is used on restore).

### CU-3.3 Render a Fixture B scene round-trips transforms
1. Create a scene from B-nested's reference pose; **Render** it.
2. Open the output PNG; compare to the CU-3.1 reference screenshot.
- **PASS**: rendered image shows the nested assembly correctly assembled; post-render
  viewport restored. **FAIL**: nested parts displaced in the PNG.

---

## §4 Per-occurrence opacity — Fixtures A & C — verifies `556a04f` + **A-2**

### CU-4.1 Single-instance opacity round-trips (Fixture A)
1. Open **A-opacity** (one occurrence at ~35%). Screenshot the viewport (note the translucent part).
2. **Capture Current State**.
3. Change that occurrence's opacity to 100% (right-click → Opacity). Confirm it looks solid.
4. **Apply Captured State**. Screenshot.
- **PASS**: the occurrence is translucent again at ~35% — the captured value is restored.
- **FAIL**: it stays at 100%. *(Original Fixture A failure: opacity read/written on the
  native component missed the per-instance override.)*

### CU-4.2 Repeated component — independent per-instance opacity (Fixture C)
1. Open **C-repeated**. Give instance 1 ~25% and instance 2 ~75% opacity. Screenshot.
2. **Capture Current State**.
3. Set both instances to 100%. **Apply Captured State**. Screenshot.
- **PASS**: instance 1 returns to ~25% and instance 2 to ~75% **independently** — the
  two instances of the same component display at different opacities.
- **FAIL**: both end at the same opacity. *(Confirms A-2: `createForAssemblyContext`
  gives a genuinely per-instance override; the old risks-doc "cannot be independently
  replayed" claim is now false.)*

### CU-4.3 Scene YAML stores opacity per occurrence (file check)
1. Create a scene from the A-opacity pose. Terminal: run the "assembly_state opacity
   placement" recipe on the new `scenes/*.yaml`.
- **PASS**: every `occurrences[]` entry has an `opacity` value; `components[]` entries
  have only `component_id`/`label` (no `opacity`).

### CU-4.4 Legacy scene still replays opacity (backward compatibility)
1. Add **legacy-scene** to the project (component-level opacity, no occurrence opacity).
   Ensure its occurrence/component IDs match live Fixture entities.
2. **Load Scene** for it; screenshot.
- **PASS**: the component's authored opacity is applied to its occurrence(s) (legacy
  fallback), and the scene validates/loads without an `OPACITY_INVALID` or schema error.

---

## §5 Regression — features PR #27 must not have broken

### CU-5.1 Per-scene camera stays distinct (individual + batch)
1. On Fixture A create three scenes with genuinely distinct, manually orbited cameras.
2. Render each individually, then also run **Render All Scenes**.
3. Terminal: pixel-diff each pair of the three outputs (`getbbox()` recipe).
- **PASS**: all three differ (`getbbox()` non-`None`) and match their orientations.
  *(Re-confirms the camera follow-up against the PR #27 code, which left camera
  capture/apply unchanged.)*

### CU-5.2 Validation still blocks bad IDs / references (Fixtures D, E)
1. Fixture E: confirm duplicate IDs are reported ("Blocking duplicate IDs found…",
   "Duplicate occurrence ID: …"), repair is explicit, render works after repair.
2. Fixture D: render/apply a scene referencing the removed occurrence.
- **PASS**: `SCENE_REFERENCE_MISSING` blocks before any mutation; duplicates block apply/render.

### CU-5.3 Reorder touches only `manual.yaml`
1. With ≥2 scenes, use **Move Up/Down**. Terminal: `git diff` the project.
- **PASS**: only `manual.yaml` scene order changes; no scene file renamed; count unchanged.

---

## §6 Troubleshooting / failure states — not previously exercised

These cover the checklist's "documented troubleshooting states" line (original report §7, priority 5).

### CU-6.1 Corrupted `manual.yaml`
1. Terminal: append a syntactically invalid line to `manual.yaml`.
2. Restart the add-in / press Refresh. Screenshot.
- **PASS**: the palette shows a clear error (`MANIFEST_INVALID`, `YAML_PARSE_FAILED`,
  or `SCHEMA_VERSION_*`) — not a blank panel or an endless "Connecting…".
3. Restore the file.

### CU-6.2 Project folder removed mid-session
1. With a project open, terminal-move the project folder aside.
2. Press **Refresh** / attempt a scene op. Screenshot.
- **PASS**: `PROJECT_ROOT_UNRESOLVED` (or a clear "open the project folder" message),
  no crash. Restore the folder afterward.

### CU-6.3 Stable-ID persistence across restart (documented behavior)
1. On a fresh Fixture A, **Ensure IDs**. **Save the Fusion document.** Restart Fusion,
   reopen the document, run the add-in. Confirm the Stable IDs section reports unique
   IDs **without** re-running Ensure IDs, and scene creation works.
2. Repeat but **do not save** before restart.
- **PASS**: saved → IDs persist; unsaved → Ensure IDs is required again and the identity
  panel prompts for it (attributes are document data; the add-in never auto-saves).

---

## Sign-off

| Test | Result (Pass/Fail) | Evidence (screenshot / terminal output) | Notes |
|---|---|---|---|
| CU-1.1 | | | |
| CU-1.2 | | | |
| CU-1.3 | | | |
| CU-1.4 | | | |
| CU-2.1 | | | |
| CU-2.2 | | | |
| CU-2.3 | | | |
| CU-3.1 | | | |
| CU-3.2 | | | |
| CU-3.3 | | | |
| CU-4.1 | | | |
| CU-4.2 | | | |
| CU-4.3 | | | |
| CU-4.4 | | | |
| CU-5.1 | | | |
| CU-5.2 | | | |
| CU-5.3 | | | |
| CU-6.1 | | | |
| CU-6.2 | | | |
| CU-6.3 | | | |

**Release gate for PR #27:** every §1–§4 test passes (these are the PR's fixes and
the A-1/A-2 assumptions), and no §5 regression. §6 items are documented-behavior /
robustness checks; record them but treat only a crash or a silent/blank failure as blocking.
