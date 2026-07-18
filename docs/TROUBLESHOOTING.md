# Troubleshooting

## Reading the palette's connection line

The palette page is self-contained and always ends in one of five explicit
states. Each one narrows the failure down:

| Connection line | Meaning | What to do |
|---|---|---|
| `Add-in connected.` | Handshake completed | Nothing — this is the healthy state |
| `Connecting to add-in… (attempt N of 40)` counting up | The page's script is running but the add-in is not answering yet | Wait up to 10 seconds; if it exhausts the attempts, see the next row |
| `Add-in did not respond after 10 seconds. …` | The add-in's Python side never answered the ping | Stop and rerun the add-in from **Utilities > Add-Ins > Scripts and Add-Ins**, then check the Text Commands window for `FMSM` lines (see below) |
| `Add-in connection error: <message>` | The add-in answered with a protocol error | Both sides are running but disagree; make sure the installed bundle is one consistent version, then report the message |
| `Connecting to add-in…` frozen with no attempt counter | The page's script never ran at all | The installed copy is stale or damaged; reinstall the whole `addin/FusionManualSceneManager` bundle and restart Fusion |

The add-in also logs breadcrumbs to Fusion's **Text Commands** window
(`FMSM: palette shown; waiting for the page's first ping.`,
`FMSM: first palette message received; …`). Whichever breadcrumb is missing
marks the step that failed.

After updating the installed files, always stop the add-in and run it again;
the add-in rebuilds its palette from scratch on every start, so a stale palette
from an earlier run cannot linger.

## The add-in appears to start but no palette opens

If Fusion loads the add-in Python entry point, it reports startup failures in two places:

1. a Fusion message dialog with a concise explanation; and
2. Fusion's **Text Commands** window, which contains the full traceback prefixed with `FMSM startup failed:`.

The add-in manifest is validated by a unit test and uses Fusion-compatible UUID and localized-description metadata. After installing an updated copy, stop the add-in and run it again from **Utilities > Add-Ins > Scripts and Add-Ins**. If the failure dialog appears, copy the entire `FMSM startup failed` traceback from Text Commands and include it in a bug report.

Register the `addin/FusionManualSceneManager` bundle itself. It must contain these sibling files:

```text
FusionManualSceneManager.py
FusionManualSceneManager.manifest
```

If it is not listed after reopening the dialog, copy the complete bundle directory to an existing Add-Ins search folder shown by Fusion.

## Run the pure-Python checks

From the repository root, run:

```bash
python3 -m pytest -q
python3 -m compileall -q addin/FusionManualSceneManager
```

These checks do not require Fusion. They cannot validate the installed Fusion runtime, palette host, or graphics driver.


## Release-candidate verification

Before treating an installed copy as release-ready, run the pure-Python checks above and then execute `docs/FUSION_ACCEPTANCE_CHECKLIST.md` inside Fusion against the required fixture assemblies. Live Fusion verification is required for camera, transform, opacity, viewport export, and restore behavior because those APIs cannot be exercised by the pure-Python unit tests.
