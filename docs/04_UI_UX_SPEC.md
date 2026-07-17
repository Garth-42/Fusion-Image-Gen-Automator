# 4. UI and UX Specification

## 4.1 Palette layout

Use a dockable palette approximately 420-520 pixels wide.

```text
┌──────────────────────────────────────────────┐
│ Fusion Manual Scene Manager           [⋯]   │
├──────────────────────────────────────────────┤
│ Project: Printer E-Box Guide          [Open] │
│ Document: Documentation Assembly       ✓     │
├──────────────────────────────────────────────┤
│ Search…                    [+ New Scene]     │
├──────────────────────────────────────────────┤
│ ⋮⋮ [thumb] Install left DIN rail       Draft│
│            Shows orientation and screws      │
│ ⋮⋮ [thumb] Install power supply        Review│
│            Shows bracket and fasteners       │
├──────────────────────────────────────────────┤
│ Scene: Install left DIN rail                 │
│ [Content] [Capture] [Output] [Validation]   │
│                                              │
│ Title                                        │
│ [__________________________________________] │
│ Description                                  │
│ [__________________________________________] │
│ Purpose                                      │
│ [__________________________________________] │
│ Instruction Markdown                         │
│ [                                          ] │
│                                              │
│ [Save Metadata]          Unsaved changes ●   │
├──────────────────────────────────────────────┤
│ [Load Scene] [Update Capture ▼] [Render]    │
│ [Restore Previous State]                     │
└──────────────────────────────────────────────┘
```

## 4.2 Scene list behavior

Each row includes:

- drag handle;
- lazy-loaded thumbnail;
- title;
- one-line description excerpt;
- status badge;
- output indicator: missing, available, or render failed;
- validation indicator.

The list supports:

- selection;
- keyboard up/down navigation;
- search over title, description, tags, and ID;
- drag reorder;
- context menu for duplicate, delete, reveal YAML, and reveal output image.

Do not load all thumbnail bytes at project-open time.

## 4.3 Project initialization flow

1. User clicks **Initialize Project**.
2. Dialog explains that a dedicated documentation assembly is strongly recommended.
3. User confirms.
4. Folder picker selects a local Git working tree or new folder.
5. User enters project title.
6. Add-in creates files/directories and associates project UUID.
7. Palette opens empty scene list and highlights **New Scene**.

## 4.4 Create-scene flow

1. User arranges the Fusion view.
2. User clicks **New Scene**.
3. Dialog requests title; description is optional.
4. Add-in ensures stable IDs on managed occurrences/components.
5. Add-in captures camera, visibility, opacity, and transforms.
6. Add-in creates scene YAML and manifest entry atomically.
7. Add-in renders thumbnail; final render is optional through a checkbox, default off.
8. New scene becomes selected.

If stable IDs cannot be assigned, no scene file is created.

## 4.5 Edit-metadata flow

- Fields are editable in the Content tab.
- UI marks dirty state immediately.
- **Save Metadata** validates and writes only metadata fields.
- Navigating away with dirty fields prompts Save, Discard, or Cancel.
- Metadata save must not recapture CAD state.

## 4.6 Update-capture flow

The **Update Capture** menu opens a checklist:

```text
[x] Camera
[x] Visibility
[x] Opacity
[x] Transforms
```

The user can update any subset. Metadata is not overwritten.

After successful capture, the scene YAML is written and the UI offers **Refresh Thumbnail**. Automatic thumbnail refresh may be enabled, but failure must not roll back the successfully saved scene state.

## 4.7 Load-scene flow

1. Validate scene and identity index.
2. If blocking errors exist, show them and do not alter Fusion.
3. Capture pre-scene session state if needed.
4. Apply scene.
5. Display warnings in the Validation tab.
6. Enable **Restore Previous State**.

Loading another scene preserves the original pre-scene state rather than replacing it with the previously loaded scene.

## 4.8 Restore flow

**Restore Previous State** restores the state captured before the first scene was loaded in the current session. After successful restore:

- clear session snapshot;
- disable Restore button;
- show success message.

If restoration is partial, keep the snapshot and display actionable errors.

## 4.9 Render flow

1. User clicks **Render**.
2. Disable mutating scene actions and show progress.
3. Validate before mutation.
4. Capture temporary pre-render state.
5. Apply scene and export final PNG.
6. Export thumbnail.
7. Restore temporary state.
8. Update thumbnail and output indicator.

If final PNG succeeds but thumbnail fails, report partial success and preserve the final PNG.

## 4.10 Duplicate flow

Duplicate creates:

- new scene UUID;
- new immutable basename;
- copied metadata with title prefixed or suffixed, recommended `Copy of ...`;
- copied captured state;
- no copied rendered images by default;
- manifest entry immediately after the source scene.

## 4.11 Delete flow

The confirmation dialog lists the scene YAML and generated assets that will be removed. Delete is disabled while the scene is loaded with an active session snapshot unless the state is restored first.

## 4.12 Validation tab

Group issues by severity:

- **Errors:** scene cannot load or render;
- **Warnings:** scene can proceed but result may need review;
- **Information:** noncritical context.

Each issue contains:

- stable code;
- human message;
- affected scene/entity label;
- suggested action.

Example:

```text
ERROR · DUPLICATE_OCCURRENCE_ID
Two current occurrences share the same FMSM identity.
Affected: DIN Rail:1, DIN Rail:2
Action: Run Repair Duplicate IDs, then review scenes referencing the old ID.
```

## 4.13 Accessibility and keyboard behavior

- All controls have labels and tooltips.
- Status is not communicated by color alone.
- List rows are keyboard selectable.
- Drag reorder has Move Up and Move Down alternatives.
- Dialog focus is trapped correctly.
- Error text is selectable and copyable.

## 4.14 Destructive and blocking states

Disable scene mutation during:

- render;
- apply/restore;
- project write;
- duplicate-ID repair.

A single operation lock in the application layer prevents concurrent Fusion state changes even if the palette sends duplicate requests.
