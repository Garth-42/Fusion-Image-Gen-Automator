from __future__ import absolute_import

import uuid

import pytest

from fmsm.application.errors import ServiceError
from fmsm.application.scene_service import SceneService
from fmsm.domain.models import new_manifest
from fmsm.infrastructure import yaml_store

PROJECT_ID = "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"


OCCURRENCE_ID = "5a1f2e1a-2c1b-4f2a-9b3c-6d7e8f901234"
COMPONENT_ID = "6b2f3e2b-3d2c-4a3b-8c4d-7e8f90123456"


class FakeFusion(object):
    def __init__(self):
        self.project_id = PROJECT_ID
        self.eye_x = 1.0
        # Capture copies these UUIDs into the scene file, so the identity of the
        # live design decides whether a capture can produce a valid scene at all.
        self.records = [{
            "occurrence_handle": "occ-1", "component_handle": "component-1",
            "component_key": "token-1", "label": "Widget:1", "component_label": "Widget",
            "occurrence_id": OCCURRENCE_ID, "component_id": COMPONENT_ID,
        }]

    def identity_records(self):
        return [dict(record) for record in self.records]

    def active_document(self):
        return {"name": "Assembly", "data_file_id": "urn:doc"}

    def read_project_id(self):
        return self.project_id

    def capture_scene_state(self):
        return {
            "camera": {
                "type": "orthographic",
                "eye_cm": [self.eye_x, 2.0, 3.0],
                "target_cm": [0.0, 0.0, 0.0],
                "up_vector": [0.0, 0.0, 1.0],
                "extents_cm": {"width": 10.0, "height": 8.0},
                "perspective_angle_rad": None,
                "is_fit_view": False,
            },
            "assembly_state": {"unlisted_occurrence_policy": "hide_and_warn", "occurrences": [], "components": []},
        }




class FakeStateService(object):
    def __init__(self):
        self.applied = []

    def apply(self, scene):
        self.applied.append(scene)
        return {"warnings": [{"code": "UNLISTED_OCCURRENCE_HIDDEN", "label": "extra"}]}


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
    fusion = FakeFusion()
    return SceneService(fusion, FakeSettings(root)), root, fusion


def test_create_from_current_persists_scene_and_manifest_entry(tmp_path):
    service, root, fusion = _service(tmp_path)

    result = service.create_from_current({"title": "Install Left DIN Rail", "instructions_markdown": "Do it."})

    scene = result["scene"]
    assert scene["title"] == "Install Left DIN Rail"
    assert scene["file"].startswith("scenes/install-left-din-rail__")
    manifest = yaml_store.load(root / "manual.yaml")
    assert manifest["project"]["scenes"] == [{"scene_id": scene["scene_id"], "file": scene["file"]}]
    payload = yaml_store.load(root / scene["file"])
    assert payload["scene"]["instructions_markdown"] == "Do it."
    assert payload["output"]["image_file"].startswith("assets/generated/install-left-din-rail__")


def test_capture_names_the_parts_missing_stable_ids_instead_of_failing_the_schema(tmp_path):
    service, root, fusion = _service(tmp_path)
    # A component whose FMSM.component_id attribute was never written. Capture
    # used to copy the empty value straight into the scene file and let the
    # schema reject it, so the palette showed
    # "COMPONENT_ID_INVALID: Component ID must be a UUID." against an
    # assembly_state.components index — naming neither the part nor the fix.
    fusion.records[0]["component_id"] = None

    with pytest.raises(ServiceError) as error:
        service.create_from_current({"title": "Blocked"})

    assert error.value.code == "IDENTITY_IDS_MISSING"
    assert "Widget" in error.value.message
    assert "Ensure IDs" in error.value.message
    # Nothing may be left behind by a capture that could not complete.
    assert yaml_store.load(root / "manual.yaml")["project"]["scenes"] == []
    assert list((root / "scenes").glob("*.yaml")) == []


def test_capture_is_blocked_while_two_entities_share_a_stable_id(tmp_path):
    service, root, fusion = _service(tmp_path)
    twin = dict(fusion.records[0])
    twin["component_key"] = "token-2"
    twin["label"] = "Widget:2"
    fusion.records.append(twin)

    with pytest.raises(ServiceError) as error:
        service.create_from_current({"title": "Blocked"})

    # Duplicates are already refused at render; refusing them at capture keeps
    # an unreplayable scene from being written in the first place.
    assert error.value.code == "DUPLICATE_OCCURRENCE_ID"
    assert "Repair Duplicate IDs" in error.value.message


def test_recapturing_an_existing_scene_is_guarded_the_same_way(tmp_path):
    service, root, fusion = _service(tmp_path)
    scene_id = service.create_from_current({"title": "Recapture"})["scene"]["scene_id"]
    before = yaml_store.load(root / service.get({"scene_id": scene_id})["file"])
    fusion.records[0]["occurrence_id"] = None

    with pytest.raises(ServiceError) as error:
        service.update_state({"scene_id": scene_id})

    assert error.value.code == "IDENTITY_IDS_MISSING"
    # The scene that was already on disk must survive a refused recapture.
    assert yaml_store.load(root / service.get({"scene_id": scene_id})["file"]) == before


def test_get_returns_editable_scene_metadata(tmp_path):
    service, root, fusion = _service(tmp_path)
    scene_id = service.create_from_current({
        "title": "Editable",
        "description": "Describe",
        "purpose": "Teach",
        "instructions_markdown": "* Step",
    })["scene"]["scene_id"]

    result = service.get({"scene_id": scene_id})

    assert result["scene_id"] == scene_id
    assert result["title"] == "Editable"
    assert result["description"] == "Describe"
    assert result["purpose"] == "Teach"
    assert result["instructions_markdown"] == "* Step"
    assert result["status"] == "draft"


def test_update_metadata_does_not_rename_or_modify_captured_state(tmp_path):
    service, root, fusion = _service(tmp_path)
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
    service, root, fusion = _service(tmp_path)
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
    service, root, fusion = _service(tmp_path)
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
    service, root, fusion = _service(tmp_path)
    first = service.create_from_current({"title": "First"})["scene"]["scene_id"]
    second = service.create_from_current({"title": "Second"})["scene"]["scene_id"]

    assert [entry["scene_id"] for entry in service.reorder({"scene_ids": [second, first]})["scenes"]] == [second, first]
    with pytest.raises(ServiceError) as error:
        service.reorder({"scene_ids": [first]})
    assert error.value.code == "SCENE_REORDER_INVALID"


def test_update_state_recaptures_graphics_without_changing_metadata_or_outputs(tmp_path):
    service, root, fusion = _service(tmp_path)
    scene_id = service.create_from_current({"title": "Pose", "instructions_markdown": "Keep"})["scene"]["scene_id"]
    entry = yaml_store.load(root / "manual.yaml")["project"]["scenes"][0]
    before = yaml_store.load(root / entry["file"])
    fusion.eye_x = 9.0

    result = service.update_state({"scene_id": scene_id})

    after = yaml_store.load(root / entry["file"])
    assert result["scene"]["scene_id"] == scene_id
    assert after["scene"] == before["scene"]
    assert after["output"] == before["output"]
    assert after["camera"]["eye_cm"] == [9.0, 2.0, 3.0]
    assert after["source"]["captured_at_utc"] >= before["source"]["captured_at_utc"]


def test_load_applies_persisted_scene_through_state_guard(tmp_path):
    service, root, fusion = _service(tmp_path)
    state_service = FakeStateService()
    service = SceneService(fusion, FakeSettings(root), state_service)
    scene_id = service.create_from_current({"title": "Saved View"})["scene"]["scene_id"]

    result = service.load({"scene_id": scene_id})

    assert result["scene"]["scene_id"] == scene_id
    assert result["warnings"] == [{"code": "UNLISTED_OCCURRENCE_HIDDEN", "label": "extra"}]
    assert state_service.applied[0]["scene"]["id"] == scene_id
