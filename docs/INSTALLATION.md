# Installation (Initial Add-in Slice)

## Requirements

- Current stable Autodesk Fusion desktop on macOS or Windows.
- A dedicated documentation assembly rather than a production master.

The add-in vendors the pure-Python portion of PyYAML, so no Python package installation or network access is required at runtime.

## Install for development

1. Clone this repository locally.
2. In Fusion, open **Utilities > Add-Ins > Scripts and Add-Ins**.
3. Select the **Add-Ins** tab, choose **+**, and select `addin/FusionManualSceneManager` from this repository.
4. Select **Fusion Manual Scene Manager** and click **Run**.
5. The palette opens and confirms its local Python-to-HTML message bridge.

Fusion loads the add-in from its selected local directory. Do not move the add-in directory while it is running.

## Initial behavior

This first committed slice provides the add-in manifest, a dockable local palette, a versioned ping protocol, vendored YAML support, and a pure-Python persistence foundation. It deliberately does not yet expose project initialization, CAD-state capture, scene CRUD, or rendering controls; those follow the implementation sequence in `05_IMPLEMENTATION_PLAN.md`.
