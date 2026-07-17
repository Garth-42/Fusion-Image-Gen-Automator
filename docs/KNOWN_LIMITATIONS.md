# Known Limitations — Initial Add-in Slice

- Project initialization/open and stable-ID management are available. Scene capture, scene CRUD, state restoration, and rendering are not wired yet.
- No Fusion scene state is captured or applied in this slice, and no rendering is performed. Stable-ID commands do write Fusion document attributes.
- The palette bridge has been unit-tested outside Fusion; Fusion event, camera, assembly, and export behavior still require the fixture-based integration tests described in `06_TEST_STRATEGY.md`.
- Vendored PyYAML is pure Python. Its optional C extension is intentionally excluded to keep the add-in portable across Fusion's supported platforms.
