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


def test_reorder_rejects_a_malformed_order_with_its_own_code(tmp_path):
    service, root, fusion = _service(tmp_path)
    first = service.create_from_current({"title": "First"})["scene"]["scene_id"]

    # Sorting a list of mixed types raises; that used to escape as INTERNAL_ERROR.
    for order in ([first, 7], [{"scene_id": first}], "not-a-list", None):
        with pytest.raises(ServiceError) as error:
            service.reorder({"scene_ids": order})
        assert error.value.code == "SCENE_REORDER_INVALID"


def test_delete_removes_a_scene_whose_file_is_broken(tmp_path):
    service, root, fusion = _service(tmp_path)
    keep = service.create_from_current({"title": "Keep"})["scene"]
    broken = service.create_from_current({"title": "Broken"})["scene"]
    (root / broken["file"]).write_text("scene: [unterminated\n", encoding="utf-8")

    # Deleting is how the user clears a broken scene out of the list, so it
    # must not require the scene to load first.
    service.delete({"scene_id": broken["scene_id"]})

    remaining = yaml_store.load(root / "manual.yaml")["project"]["scenes"]
    assert [entry["scene_id"] for entry in remaining] == [keep["scene_id"]]
    assert not (root / broken["file"]).exists()


def test_delete_keeps_the_scene_file_when_the_manifest_cannot_be_written(tmp_path, monkeypatch):
    service, root, fusion = _service(tmp_path)
    scene = service.create_from_current({"title": "Survivor"})["scene"]

    def failing_write(*args):
        raise OSError("disk full")
    monkeypatch.setattr(yaml_store, "write", failing_write)

    with pytest.raises(ServiceError) as error:
        service.delete({"scene_id": scene["scene_id"]})

    # The manifest still lists the scene, so its file must still be there.
    assert error.value.code == "PROJECT_WRITE_FAILED"
    assert (root / scene["file"]).is_file()


def test_create_leaves_no_orphan_scene_file_when_the_manifest_write_fails(tmp_path, monkeypatch):
    service, root, fusion = _service(tmp_path)
    real_write = yaml_store.write

    def manifest_fails(write_root, relative, data):
        if relative == "manual.yaml":
            raise OSError("disk full")
        return real_write(write_root, relative, data)
    monkeypatch.setattr(yaml_store, "write", manifest_fails)

    with pytest.raises(ServiceError):
        service.create_from_current({"title": "Orphan"})

    assert list((root / "scenes").iterdir()) == []


def test_a_corrupt_manifest_is_reported_with_a_stable_code(tmp_path):
    service, root, fusion = _service(tmp_path)
    (root / "manual.yaml").write_text("project: [unterminated\n", encoding="utf-8")

    with pytest.raises(ServiceError) as error:
        service.list({})

    assert error.value.code == "YAML_PARSE_FAILED"
    assert not error.value.message.startswith("YAML_PARSE_FAILED")


def test_scene_actions_refuse_a_manifest_that_belongs_to_another_project(tmp_path):
    service, root, fusion = _service(tmp_path)
    yaml_store.write(root, "manual.yaml", new_manifest("99999999-9999-4999-8999-999999999999", "Other", "Assembly", "urn:doc"))

    with pytest.raises(ServiceError) as error:
        service.create_from_current({"title": "Wrong project"})

    assert error.value.code == "PROJECT_ID_MISMATCH"


def test_thumbnails_returns_only_requested_scenes_that_have_one(tmp_path):
    service, root, fusion = _service(tmp_path)
    rendered = service.create_from_current({"title": "Rendered"})["scene"]
    pending = service.create_from_current({"title": "Pending"})["scene"]
    other = service.create_from_current({"title": "Not asked for"})["scene"]
    yaml_store.project_path(root, rendered["output"]["thumbnail_file"]).write_bytes(b"fake png")
    yaml_store.project_path(root, other["output"]["thumbnail_file"]).write_bytes(b"other png")

    result = service.thumbnails({"scene_ids": [rendered["scene_id"], pending["scene_id"]]})["thumbnails"]

    assert sorted(result) == sorted([rendered["scene_id"], pending["scene_id"]])
    assert result[rendered["scene_id"]]["data_uri"] == "data:image/png;base64,ZmFrZSBwbmc="
    assert result[rendered["scene_id"]]["version"]
    assert result[pending["scene_id"]] is None


def test_thumbnails_rejects_a_malformed_request(tmp_path):
    service, root, fusion = _service(tmp_path)
    with pytest.raises(ServiceError) as error:
        service.thumbnails({"scene_ids": "all"})
    assert error.value.code == "INVALID_PALETTE_REQUEST"
