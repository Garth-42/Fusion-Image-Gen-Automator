from __future__ import absolute_import

import pytest

from fmsm.application.errors import ServiceError
from fmsm.application.render_service import RenderService
from fmsm.application.scene_service import SceneService
from fmsm.domain.models import new_manifest
from fmsm.infrastructure import yaml_store

PROJECT_ID = "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"


class FakeFusion(object):
    def __init__(self):
        self.project_id = PROJECT_ID
        self.exports = []
        self.restored = 0
        self.applied = 0
        self.fail_export = False
        self.restore_error = None
        self.reference_issues = []

    def active_document(self):
        return {"name": "Assembly", "data_file_id": "urn:doc"}

    def read_project_id(self):
        return self.project_id

    def capture_scene_state(self):
        return {
            "camera": {
                "type": "orthographic", "eye_cm": [1.0, 2.0, 3.0], "target_cm": [0.0, 0.0, 0.0],
                "up_vector": [0.0, 0.0, 1.0], "extents_cm": {"width": 10.0, "height": 8.0},
                "perspective_angle_rad": None, "is_fit_view": False,
            },
            "assembly_state": {"unlisted_occurrence_policy": "hide_and_warn", "occurrences": [], "components": []},
        }

    def validate_scene_references(self, scene):
        return list(self.reference_issues)

    def capture_session_state(self):
        return {"session": "before"}

    def apply_scene_state(self, scene):
        self.applied += 1
        return {"warnings": [{"code": "UNLISTED_OCCURRENCE_HIDDEN", "label": "extra"}]}

    def refresh_viewport(self):
        pass

    def export_viewport_png(self, path, width_px, height_px, transparent_background, anti_alias):
        if self.fail_export:
            raise RuntimeError("disk full")
        self.exports.append((path, width_px, height_px, transparent_background, anti_alias))
        with open(path, "w", encoding="utf-8") as target:
            target.write("png")

    def restore_session_state(self, snapshot):
        self.restored += 1
        if self.restore_error is not None:
            raise self.restore_error


class FakeSettings(object):
    def __init__(self, root):
        self.root = str(root)

    def project_root(self, project_id):
        return self.root if project_id == PROJECT_ID else None


def _services(tmp_path):
    root = tmp_path / "repo"
    for relative in ("scenes", "assets/generated", "assets/thumbnails"):
        yaml_store.project_path(root, relative).mkdir(parents=True, exist_ok=True)
    yaml_store.write(root, "manual.yaml", new_manifest(PROJECT_ID, "Guide", "Assembly", "urn:doc"))
    fusion = FakeFusion()
    settings = FakeSettings(root)
    scene = SceneService(fusion, settings).create_from_current({"title": "Render Me"})["scene"]
    return RenderService(fusion, settings), fusion, root, scene


def test_render_exports_final_and_thumbnail_then_restores(tmp_path):
    service, fusion, root, scene = _services(tmp_path)

    result = service.render({"scene_id": scene["scene_id"]})

    assert result["image_file"].startswith("assets/generated/render-me__")
    assert result["thumbnail_file"].startswith("assets/thumbnails/render-me__")
    assert fusion.applied == 1
    assert fusion.restored == 1
    assert len(fusion.exports) == 2
    assert fusion.exports[0][1:3] == (2400, 1600)
    assert fusion.exports[1][1:3] == (480, 320)
    assert yaml_store.project_path(root, result["image_file"]).read_text(encoding="utf-8") == "png"
    assert result["warnings"][0]["code"] == "UNLISTED_OCCURRENCE_HIDDEN"


def test_render_validates_references_before_mutating(tmp_path):
    service, fusion, root, scene = _services(tmp_path)
    fusion.reference_issues = [{"code": "SCENE_REFERENCE_MISSING", "message": "missing"}]

    with pytest.raises(ServiceError) as error:
        service.render({"scene_id": scene["scene_id"]})

    assert error.value.code == "SCENE_REFERENCE_MISSING"
    assert fusion.applied == 0
    assert fusion.exports == []
    assert fusion.restored == 0


def test_render_restores_after_export_failure(tmp_path):
    service, fusion, root, scene = _services(tmp_path)
    fusion.fail_export = True

    with pytest.raises(ServiceError) as error:
        service.render({"scene_id": scene["scene_id"]})

    assert error.value.code == "RENDER_FAILED"
    assert fusion.applied == 1
    assert fusion.restored == 1


def test_restore_failure_is_reported(tmp_path):
    service, fusion, root, scene = _services(tmp_path)
    fusion.restore_error = RuntimeError("locked")

    with pytest.raises(ServiceError) as error:
        service.render({"scene_id": scene["scene_id"]})

    assert error.value.code == "STATE_RESTORE_FAILED"
    assert fusion.restored == 1
