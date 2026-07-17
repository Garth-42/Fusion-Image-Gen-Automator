# Known Limitations — Initial Add-in Slice

- Project initialization/open and stable-ID management are available. Scene persistence, scene CRUD, and rendering are not wired yet.
- Guarded Fusion state application/restoration is available to the application layer but is not yet exposed until scene creation and loading are implemented. Stable-ID commands do write Fusion document attributes.
- The palette bridge has been unit-tested outside Fusion; Fusion event, camera, assembly, and export behavior still require the fixture-based integration tests described in `06_TEST_STRATEGY.md`.
- Vendored PyYAML is pure Python. Its optional C extension is intentionally excluded to keep the add-in portable across Fusion's supported platforms.
