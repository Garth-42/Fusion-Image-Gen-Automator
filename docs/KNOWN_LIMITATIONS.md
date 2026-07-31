# Known Limitations — Initial Add-in Slice

- Project initialization/open, stable-ID management, guarded state preview, scene YAML CRUD, and guarded final/thumbnail PNG rendering are available.
- The palette can create scene YAML from the current state, list scene titles, edit scene metadata and instructions, reorder scenes with button controls, render final/thumbnail PNGs, duplicate scenes, delete scenes, and use guarded state preview/restore.
- The palette bridge has been unit-tested outside Fusion; Fusion event, camera, assembly, and export behavior still require the fixture-based integration tests described in `06_TEST_STRATEGY.md`.
- Vendored PyYAML is pure Python. Its optional C extension is intentionally excluded to keep the add-in portable across Fusion's supported platforms.

## Stable IDs on externally referenced components are not persistable

A component inserted from another Fusion document is an *externally referenced*
component: Fusion keeps its attributes — including the stable `component_id`
this add-in assigns — in that other document, not in the assembly you have open.
Saving the assembly does not save that document, so the ID is gone at the next
launch and **Ensure IDs** has to be clicked again.

Round-4 §S4.2 established this against a live Fusion session, reproducibly:

- Saving the root assembly reported success while the referenced document
  object stayed modified.
- Opening the referenced component in its own tab and saving it there did not
  help; Fusion held a second, unmodified in-memory copy of that document, and
  the copy carrying the new attribute was not the one being saved.
- **Edit In Place** left `File → Save` greyed out for the modified copy
  entirely.

There is currently no user action that persists it, and Fusion reports the
document as fully saved throughout — no warning, no "recover unsaved work"
prompt. The add-in cannot change that, so it reports it: the **Stable IDs**
panel names the linked components, and **Ensure IDs** says which of the IDs it
just assigned will not survive reopening.

Native (non-referenced) occurrences and components are unaffected — their IDs
persist through an ordinary save and a full Fusion restart, confirmed in the
same session by direct contrast.

**Working around it:** build the documentation assembly from components that
live in the assembly's own document. Where a linked component is unavoidable,
expect to click **Ensure IDs** once per Fusion session, and recapture any scene
that referenced the old ID.
