# Installation (Initial Add-in Slice)

## Requirements

- Current stable Autodesk Fusion desktop on macOS or Windows.
- A dedicated documentation assembly rather than a production master.

The add-in vendors the pure-Python portion of PyYAML, so no Python package installation or network access is required at runtime.

## Install for development

In the current Fusion Add-Ins dialog, register the add-in bundle directory itself. Select `FusionManualSceneManager`, which contains the matching `.py` entry point and `.manifest` file.

1. Clone this repository locally.
2. In Fusion, open **Utilities > Add-Ins > Scripts and Add-Ins**.
3. Select the **Add-Ins** tab and click **+**.
4. Select this add-in bundle directory from the repository:

   ```text
   Fusion-Image-Gen-Automator/addin/FusionManualSceneManager
   ```

5. Close and reopen the **Scripts and Add-Ins** dialog. The add-in list should now contain **Fusion Manual Scene Manager**.
6. Select it and click **Run**. The palette opens and confirms its local Python-to-HTML message bridge.

### If the add-in still is not listed

Copy the complete `FusionManualSceneManager` directory—not just its `.py` file—to one of Fusion's existing Add-Ins folders shown in the dialog. The copied directory must contain these sibling files:

```text
FusionManualSceneManager/
├── FusionManualSceneManager.py
└── FusionManualSceneManager.manifest
```

Then close and reopen the dialog. If the add-in is listed but fails after clicking **Run**, follow `TROUBLESHOOTING.md` to collect the startup traceback.

## Initial behavior

This implementation provides the add-in manifest, a dockable local palette, project initialization/open, stable occurrence/component UUID management, vendored YAML support, and a pure-Python persistence foundation. It deliberately does not yet expose CAD-state capture, scene CRUD, state restoration, or rendering controls; those follow the implementation sequence in `05_IMPLEMENTATION_PLAN.md`.
