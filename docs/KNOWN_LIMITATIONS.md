# Known Limitations — Initial Add-in Slice

- Project initialization/open, stable-ID management, guarded state preview, scene YAML CRUD, and guarded final/thumbnail PNG rendering are available.
- The palette can create scene YAML from the current state, list scene titles, edit scene metadata and instructions, reorder scenes with button controls, render final/thumbnail PNGs, duplicate scenes, delete scenes, and use guarded state preview/restore.
- The palette bridge has been unit-tested outside Fusion; Fusion event, camera, assembly, and export behavior still require the fixture-based integration tests described in `06_TEST_STRATEGY.md`.
- Vendored PyYAML is pure Python. Its optional C extension is intentionally excluded to keep the add-in portable across Fusion's supported platforms.
