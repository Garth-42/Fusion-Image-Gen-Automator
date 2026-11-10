# Known Limitations — Initial Add-in Slice

- Project initialization/open, stable-ID management, guarded state preview, scene YAML CRUD, and guarded final/thumbnail PNG rendering are available.
- The palette can create scene YAML from the current state, list scene titles, edit scene metadata and instructions, reorder scenes with button controls, render final/thumbnail PNGs, duplicate scenes, delete scenes, and use guarded state preview/restore.
- The palette bridge has been unit-tested outside Fusion; Fusion event, camera, assembly, and export behavior still require the fixture-based integration tests described in `06_TEST_STRATEGY.md`.
- Vendored PyYAML is pure Python. Its optional C extension is intentionally excluded to keep the add-in portable across Fusion's supported platforms.
- The project link is stored in the Fusion document, which the add-in never saves. If the document is closed without saving, the link is lost; the palette then offers to reopen the project file remembered for that document on this computer.
- Opacity is a component-level property in the Fusion API, so occurrences of the same component cannot hold different opacities in one scene.
- The pre-scene snapshot used by **Restore Previous View** belongs to the document that was active when a scene was first shown. Restore before switching to another Fusion document.
