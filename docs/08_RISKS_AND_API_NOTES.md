# 8. Risks, Limitations, and Fusion API Notes

## 8.1 Major risks

| Risk | Impact | First-deliverable mitigation |
|---|---|---|
| Scene transforms modify the active design state | Accidental changes or dirty document | Require dedicated documentation assembly; capture and restore session state; never auto-save |
| Opacity overrides live on per-occurrence proxies, not the shared native component | Authored per-instance opacity is not replayed | Capture and restore each occurrence's assembly-context opacity override via component proxies; confirm in the fixture pass |
| IDs duplicate after copy/paste | Ambiguous scene references | UUID scan before apply/render; block on duplicate; explicit repair workflow |
| Browser names change | Broken name-based references | UUID attributes are identity; names are labels only |
| External referenced components change structure | Missing scene references | Validate before mutation; show broken references; manual recapture in MVP |
| Palette and backend become tightly coupled | Difficult testing and maintenance | Versioned JSON protocol and application services |
| YAML is partially written | Lost manual source | Atomic replacement and parse-after-write |
| Absolute paths leak into Git | Poor collaboration portability | Store path only in local settings; repository stores relative paths |
| Fusion API behavior differs by OS/version | Integration defects | Supported-API-only adapters, fixture matrix, version logging |
| Scope expands into publishing/CI | MVP never finishes | Explicit roadmap boundary and Codex scope guard |

## 8.2 Supported Fusion API concepts

The architecture relies on official Fusion API capabilities:

- Custom palettes can be created by an add-in and communicate with Python through palette events. The palette's JavaScript cannot call the Fusion API directly.
- The Camera object exposes eye, target, up vector, camera type, perspective angle, and orthographic extents.
- `Viewport.saveAsImageFileWithOptions` supports high-resolution render output, anti-aliasing, and transparent backgrounds.
- Fusion entities, including occurrences, expose attribute collections suitable for stable add-in metadata.
- Occurrence light-bulb state is writable; effective visibility is context-dependent.
- Occurrence `transform2` replaces the retired `transform` property; root-component batch transforms are available through `transformOccurrences`.
- Component revision IDs exist and can support future stale-scene tracking, but are intentionally not used in the first deliverable.
- Documents expose modified/up-to-date state and can update external references, but the first deliverable does not update references automatically.

## 8.3 API implementation cautions

### Palette thread and event lifetime

Keep event-handler instances in a module-level or add-in-lifetime collection. Do not let Python garbage collection remove handlers. All Fusion API operations should run from Fusion event callbacks, not worker threads.

### Camera

- A camera retrieved from a viewport is a copy.
- Modify the copy and assign it back to the viewport.
- Set smooth transition off for deterministic scene application.
- Use `getExtents`/`setExtents`; do not use the retired `viewExtents` property.

### Transforms

- Use `transform2`, not retired `transform`.
- Resolve nested occurrences into root context before batch transformation.
- Use full matrices in persistence.
- Decide and document whether joints are ignored; scene presentation requires `ignoreJoints=True`, but this reinforces the dedicated-documentation-assembly requirement.

### Visibility

Use `isLightBulbOn` for replay. `isVisible` is effective read-only visibility and includes parent context; it is useful for diagnostics but not sufficient for state restoration.

### Opacity

Opacity overrides are per-occurrence and live on the component proxy in each occurrence's assembly context, not on the shared native component returned by `Occurrence.component`. Capture and restore opacity through `Component.createForAssemblyContext(occurrence).opacity` so per-instance overrides round-trip. `Occurrence.visibleOpacity` is the combined inherited result and is read-only, so it is for diagnostics only, not restoration.

### Transforms in assembly context

Replay occurrence transforms with `rootComponent.transformOccurrences(occurrences, transforms, ignoreJoints=True)`, not per-occurrence `transform2` assignment. Setting `transform2` one occurrence at a time drags nested children when their parent moves; the batch call flattens the assembly and applies every transform in root context at once.

### Rendering

Create `SaveImageFileOptions`, set filename, dimensions, anti-aliasing, and transparent-background option, then call `saveAsImageFileWithOptions`. Verify the return value and file existence/readability.

### External references

The first deliverable should warn if the document is not up to date. Do not call `updateAllReferences` automatically. A later explicit command may do so with confirmation.

## 8.4 Official reference links

1. Autodesk, *Using Palettes and Browser Command Inputs*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Palettes_UM.htm
2. Autodesk, *Palettes.add Method*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Palettes_add.htm
3. Autodesk, *Camera Object*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Camera.htm
4. Autodesk, *Camera.setExtents Method*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Camera_setExtents.htm
5. Autodesk, *Viewport.saveAsImageFileWithOptions Method*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Viewport_saveAsImageFileWithOptions.htm
6. Autodesk, *SaveImageFileOptions Object*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/SaveImageFileOptions.htm
7. Autodesk, *Attributes Object*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Attributes.htm
8. Autodesk, *Occurrence.attributes Property*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrence_attributes.htm
9. Autodesk, *Occurrence Object*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrence.htm
10. Autodesk, *Component.transformOccurrences Method*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Component_transformOccurrences.htm
11. Autodesk, *Component.opacity Property*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Component_opacity.htm
12. Autodesk, *Component Object* (`revisionId`): https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Component.htm
13. Autodesk, *Document.updateAllReferences Method*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Document_updateAllReferences.htm
14. Autodesk, *Document Object*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Document.htm
15. Autodesk, *Using the Python Add-in Template*: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/PythonTemplate_UM.htm

References should be rechecked during implementation because Fusion is continuously updated.
