# Troubleshooting

## The add-in appears to start but no palette opens

If Fusion loads the add-in Python entry point, it reports startup failures in two places:

1. a Fusion message dialog with a concise explanation; and
2. Fusion's **Text Commands** window, which contains the full traceback prefixed with `FMSM startup failed:`.

The add-in manifest is validated by a unit test and uses Fusion-compatible UUID and localized-description metadata. After installing an updated copy, stop the add-in and run it again from **Utilities > Add-Ins > Scripts and Add-Ins**. If the failure dialog appears, copy the entire `FMSM startup failed` traceback from Text Commands and include it in a bug report.

Verify that Fusion lists the add-in whose directory contains both of these files:

```text
FusionManualSceneManager.py
FusionManualSceneManager.manifest
```

Do not select the repository root or the `addin/` parent directory; select `addin/FusionManualSceneManager` itself.

## Run the pure-Python checks

From the repository root, run:

```bash
python3 -m pytest -q
python3 -m compileall -q addin/FusionManualSceneManager
```

These checks do not require Fusion. They cannot validate the installed Fusion runtime, palette host, or graphics driver.
