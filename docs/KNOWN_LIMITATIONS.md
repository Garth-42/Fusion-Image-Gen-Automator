# Known Limitations — Initial Add-in Slice

- Project initialization/open, stable-ID management, guarded state preview, and scene YAML CRUD are available. Rendering is not wired yet.
- The palette can create scene YAML from the current state, list scene titles, duplicate scenes, delete scenes, and use guarded state preview/restore. Metadata editing and reordering are available through the message protocol and are not yet represented by full palette forms.
- The palette bridge has been unit-tested outside Fusion; Fusion event, camera, assembly, and export behavior still require the fixture-based integration tests described in `06_TEST_STRATEGY.md`.
- Vendored PyYAML is pure Python. Its optional C extension is intentionally excluded to keep the add-in portable across Fusion's supported platforms.
