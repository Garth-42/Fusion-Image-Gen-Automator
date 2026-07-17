# Known Limitations — Initial Add-in Slice

- The palette currently validates only a local `system.ping` request. Project and scene actions are not wired yet.
- No Fusion document state is captured or modified in this slice, and no rendering is performed.
- The palette bridge has been unit-tested outside Fusion; Fusion event, camera, assembly, and export behavior still require the fixture-based integration tests described in `06_TEST_STRATEGY.md`.
- Vendored PyYAML is pure Python. Its optional C extension is intentionally excluded to keep the add-in portable across Fusion's supported platforms.
