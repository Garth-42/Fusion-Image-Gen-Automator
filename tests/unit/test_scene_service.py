from __future__ import absolute_import

import uuid

import pytest

from fmsm.application.errors import ServiceError
from fmsm.application.scene_service import SceneService
from fmsm.domain.models import new_manifest
from fmsm.infrastructure import yaml_store

PROJECT_ID = "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"


class FakeFusion(object):
    def __init__(self):
        self.project_id = PROJECT_ID

    def active_document(self):
        return {"name": "Assembly", "data_file_id": "urn:doc"}

    def read_project_id(self):
        return self.project_id

    def capture_scene_state(self):
        return {
            "camera": {
                "type": "orthographic",
                "eye_cm": [1.0, 2.0, 3.0],
                "target_cm": [0.0, 0.0, 0.0],
                "up_vector": [0.0, 0.0, 1.0],
                "extents_cm": {"width": 10.0, "height": 8.0},
                "perspective_angle_rad": None,
                "is_fit_view": False,
            },
            "assembly_state": {"unlisted_occurrence_policy": "hide_and_warn", "occurrences": [], "components": []},
        }


class FakeSettings(object):
    def __init__(self, root):
        self.root = str(root)

    def project_root(self, project_id):
        return self.root if project_id == PROJECT_ID else None


def _service(tmp_path):
    root = tmp_path / "repo"
    for relative in ("scenes", "assets/generated", "assets/thumbnails"):
        yaml_store.project_path(root, relative).mkdir(parents=True, exist_ok=True)
    yaml_store.write(root, "manual.yaml", new_manifest(PROJECT_ID, "Guide", "Assembly", "urn:doc"))
    return SceneService(FakeFusion(), FakeSettings(root)), root


def test_create_from_current_persists_scene_and_manifest_entry(tmp_path):
    service, root = _service(tmp_path)

    result = service.create_from_current({"title": "Install Left DIN Rail", "instructions_markdown": "Do it."})

    scene = result["scene"]
    assert scene["title"] == "Install Left DIN Rail"
    assert scene["file"].startswith("scenes/install-left-din-rail__")
    manifest = yaml_store.load(root / "manual.yaml")
    assert manifest["project"]["scenes"] == [{"scene_id": scene["scene_id"], "file": scene["file"]}]
    payload = yaml_store.load(root / scene["file"])
    assert payload["scene"]["instructions_markdown"] == "Do it."
    assert payload["output"]["image_file"].startswith("assets/generated/install-left-din-rail__")


def test_update_metadata_does_not_rename_or_modify_captured_state(tmp_path):
    service, root = _service(tmp_path)
    scene_id = service.create_from_current({"title": "First"})["scene"]["scene_id"]
    entry = yaml_store.load(root / "manual.yaml")["project"]["scenes"][0]
    before = yaml_store.load(root / entry["file"])

    service.update_metadata({"scene_id": scene_id, "title": "Renamed", "status": "review"})

    after_manifest = yaml_store.load(root / "manual.yaml")
    after = yaml_store.load(root / entry["file"])
    assert after_manifest["project"]["scenes"][0]["file"] == entry["file"]
    assert after["scene"]["title"] == "Renamed"
    assert after["scene"]["status"] == "review"
    assert after["camera"] == before["camera"]
    assert after["assembly_state"] == before["assembly_state"]


def test_duplicate_uses_new_scene_id_and_output_paths(tmp_path):
    service, root = _service(tmp_path)
    original_id = service.create_from_current({"title": "Original"})["scene"]["scene_id"]

    duplicate = service.duplicate({"scene_id": original_id})["scene"]

    assert duplicate["scene_id"] != original_id
    uuid.UUID(duplicate["scene_id"])
    manifest = yaml_store.load(root / "manual.yaml")
    assert [entry["scene_id"] for entry in manifest["project"]["scenes"]] == [original_id, duplicate["scene_id"]]
    original = yaml_store.load(root / manifest["project"]["scenes"][0]["file"])
    copied = yaml_store.load(root / manifest["project"]["scenes"][1]["file"])
    assert copied["output"]["image_file"] != original["output"]["image_file"]


def test_delete_removes_scene_and_known_assets_inside_project_root(tmp_path):
    service, root = _service(tmp_path)
    scene_id = service.create_from_current({"title": "Delete Me"})["scene"]["scene_id"]
    entry = yaml_store.load(root / "manual.yaml")["project"]["scenes"][0]
    scene = yaml_store.load(root / entry["file"])
    for relative in (scene["output"]["image_file"], scene["output"]["thumbnail_file"]):
        path = yaml_store.project_path(root, relative)
        path.write_text("png", encoding="utf-8")

    result = service.delete({"scene_id": scene_id})

    assert result["deleted"] == scene_id
    assert yaml_store.load(root / "manual.yaml")["project"]["scenes"] == []
    assert not (root / entry["file"]).exists()
    assert not yaml_store.project_path(root, scene["output"]["image_file"]).exists()


def test_reorder_requires_exact_scene_ids(tmp_path):
    service, root = _service(tmp_path)
    first = service.create_from_current({"title": "First"})["scene"]["scene_id"]
    second = service.create_from_current({"title": "Second"})["scene"]["scene_id"]

    assert [entry["scene_id"] for entry in service.reorder({"scene_ids": [second, first]})["scenes"]] == [second, first]
    with pytest.raises(ServiceError) as error:
        service.reorder({"scene_ids": [first]})
    assert error.value.code == "SCENE_REORDER_INVALID"
