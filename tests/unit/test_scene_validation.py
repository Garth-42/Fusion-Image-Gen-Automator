from __future__ import absolute_import

import copy

from fmsm.domain.validation import validate_scene


def _valid_scene():
    return {
        "schema_version": 1,
        "scene": {"id": "11111111-1111-4111-8111-111111111111", "title": "Install rail", "status": "draft", "description": "", "purpose": "", "instructions_markdown": "", "tags": []},
        "camera": {"type": "orthographic", "eye_cm": [1.0, 0.0, 0.0], "target_cm": [0.0, 0.0, 0.0], "up_vector": [0.0, 0.0, 1.0], "extents_cm": {"width": 10.0, "height": 8.0}, "perspective_angle_rad": None},
        "assembly_state": {
            "occurrences": [{"occurrence_id": "22222222-2222-4222-8222-222222222222", "visible": True, "transform_matrix_cm": [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]}],
            "components": [{"component_id": "33333333-3333-4333-8333-333333333333", "opacity": 0.5}],
        },
        "output": {"image_file": "assets/generated/install-rail__11111111.png", "thumbnail_file": "assets/thumbnails/install-rail__11111111.png", "width_px": 2400, "height_px": 1600, "thumbnail_width_px": 480, "thumbnail_height_px": 320, "transparent_background": True, "anti_alias": True},
    }


def _codes(scene):
    return [issue.code for issue in validate_scene(scene)]


def test_valid_scene_schema_passes():
    assert validate_scene(_valid_scene()) == []


def test_scene_metadata_and_output_are_validated():
    scene = _valid_scene()
    scene["scene"]["title"] = ""
    scene["scene"]["status"] = "published"
    scene["scene"]["tags"] = ["ok", 3]
    scene["output"]["image_file"] = "../escape.png"
    scene["output"]["width_px"] = 1
    scene["output"]["anti_alias"] = "yes"

    codes = _codes(scene)

    assert "SCENE_TITLE_INVALID" in codes
    assert "SCENE_STATUS_INVALID" in codes
    assert "SCENE_TAGS_INVALID" in codes
    assert "OUTPUT_PATH_UNSAFE" in codes
    assert "OUTPUT_INVALID" in codes


def test_scene_camera_occurrence_and_component_state_are_validated():
    scene = _valid_scene()
    scene["camera"]["extents_cm"]["width"] = 0
    scene["assembly_state"]["occurrences"][0]["visible"] = "yes"
    scene["assembly_state"]["occurrences"][0]["transform_matrix_cm"] = [1.0]
    scene["assembly_state"]["components"][0]["component_id"] = "not-a-uuid"
    scene["assembly_state"]["components"][0]["opacity"] = 1.5

    codes = _codes(scene)

    assert "CAMERA_INVALID" in codes
    assert "VISIBILITY_INVALID" in codes
    assert "TRANSFORM_INVALID" in codes
    assert "COMPONENT_ID_INVALID" in codes
    assert "OPACITY_INVALID" in codes


def test_occurrence_opacity_is_optional_but_validated_when_present():
    scene = _valid_scene()
    # Occurrences in _valid_scene() carry no opacity; that must stay valid so
    # scenes written before per-occurrence opacity still load.
    assert validate_scene(scene) == []
    scene["assembly_state"]["occurrences"][0]["opacity"] = 0.5
    assert validate_scene(scene) == []
    scene["assembly_state"]["occurrences"][0]["opacity"] = 1.5
    assert "OPACITY_INVALID" in _codes(scene)


def test_component_opacity_is_now_optional():
    scene = _valid_scene()
    del scene["assembly_state"]["components"][0]["opacity"]
    assert validate_scene(scene) == []


def test_perspective_scene_requires_positive_angle():
    scene = _valid_scene()
    scene["camera"]["type"] = "perspective"
    scene["camera"]["extents_cm"] = None
    scene["camera"]["perspective_angle_rad"] = 0

    assert _codes(scene) == ["CAMERA_INVALID"]
