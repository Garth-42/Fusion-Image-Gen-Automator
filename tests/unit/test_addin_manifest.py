import json
import uuid
from pathlib import Path


MANIFEST_PATH = Path(__file__).resolve().parents[2] / "addin" / "FusionManualSceneManager" / "FusionManualSceneManager.manifest"


def test_manifest_has_fusion_loadable_required_metadata():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["autodeskProduct"] == "Fusion360"
    assert manifest["type"] == "addin"
    assert uuid.UUID(manifest["id"])
    assert manifest["supportedOS"] == "windows|mac"
    assert manifest["editEnabled"] is True
    assert isinstance(manifest["description"], dict)
    assert manifest["description"][""]


def test_addin_bundle_has_a_matching_entry_point():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    bundle = MANIFEST_PATH.parent

    assert (bundle / (MANIFEST_PATH.stem + ".py")).is_file()
    assert bundle.parent.name == "addin"
    assert manifest["type"] == "addin"
