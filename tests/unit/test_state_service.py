import sys
from pathlib import Path

import pytest

ADDIN_ROOT = Path(__file__).resolve().parents[2] / "addin" / "FusionManualSceneManager"
if str(ADDIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDIN_ROOT))

from fmsm.application.errors import ServiceError
from fmsm.application.state_service import SceneStateService


class FakeFusion(object):
    def __init__(self, fail_apply=False, fail_refresh=False, references=None):
        self.events = []
        self.fail_apply = fail_apply
        self.fail_refresh = fail_refresh
        self.references = references or []

    def capture_session_state(self):
        self.events.append("capture")
        return {"camera": "before"}

    def capture_scene_state(self):
        return scene_state()

    def validate_scene_references(self, scene):
        self.events.append("validate_references")
        return self.references

    def apply_scene_state(self, scene):
        self.events.append("apply")
        if self.fail_apply:
            raise RuntimeError("export failed")
        return {"warnings": []}

    def restore_session_state(self, snapshot):
        self.events.append(("restore", snapshot))

    def refresh_viewport(self):
        self.events.append("refresh")
        if self.fail_refresh:
            raise RuntimeError("refresh failed")


def scene():
    return {
        "schema_version": 1,
        "scene": {"id": "11111111-1111-4111-8111-111111111111", "title": "State", "status": "draft"},
        "camera": {"type": "orthographic", "eye_cm": [1, 0, 0], "target_cm": [0, 0, 0], "up_vector": [0, 0, 1], "extents_cm": {"width": 10, "height": 8}, "perspective_angle_rad": None},
        "assembly_state": {"occurrences": [], "components": []},
        "output": {"image_file": "assets/generated/state.png", "thumbnail_file": "assets/thumbnails/state.png", "width_px": 2400, "height_px": 1600, "thumbnail_width_px": 480, "thumbnail_height_px": 320, "transparent_background": True, "anti_alias": True},
    }


def scene_state():
    result = scene()
    return {"camera": result["camera"], "assembly_state": {"occurrences": [], "components": []}}


def test_capture_and_apply_current_state_are_user_reachable_handlers():
    fusion = FakeFusion()
    service = SceneStateService(fusion)

    assert service.capture_current({}) == {"captured": True, "occurrences": 0, "components": 0}
    assert service.apply_captured({}) == {"warnings": []}


def test_apply_validates_references_before_capturing_or_mutating():
    fusion = FakeFusion(references=[{"code": "SCENE_REFERENCE_MISSING", "message": "Missing rail."}])

    with pytest.raises(ServiceError, match="Missing rail"):
        SceneStateService(fusion).apply(scene())

    assert fusion.events == ["validate_references"]


def test_apply_keeps_a_pre_scene_snapshot_until_explicit_restore():
    fusion = FakeFusion()
    service = SceneStateService(fusion)

    assert service.apply(scene()) == {"warnings": []}
    assert service.restore({}) == {"restored": True}

    assert fusion.events == ["validate_references", "capture", "apply", "refresh", ("restore", {"camera": "before"}), "refresh"]


def test_apply_failure_restores_state_before_reraising_the_original_error():
    fusion = FakeFusion(fail_apply=True)

    with pytest.raises(RuntimeError, match="export failed"):
        SceneStateService(fusion).apply(scene())

    assert fusion.events == ["validate_references", "capture", "apply", ("restore", {"camera": "before"}), "refresh"]


def test_viewport_refresh_failure_also_restores_state():
    fusion = FakeFusion(fail_refresh=True)

    with pytest.raises(ServiceError, match="could not fully restore"):
        SceneStateService(fusion).apply(scene())

    assert fusion.events == ["validate_references", "capture", "apply", "refresh", ("restore", {"camera": "before"}), "refresh"]
