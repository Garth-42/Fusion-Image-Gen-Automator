from __future__ import absolute_import

import sys
from pathlib import Path

import pytest

ADDIN_ROOT = Path(__file__).resolve().parents[2] / "addin" / "FusionManualSceneManager"
if str(ADDIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDIN_ROOT))

from fmsm.application.errors import ServiceError
from fmsm.application.preview_service import PreviewService
from fmsm.application.scene_service import SceneService
from fmsm.domain.models import new_manifest
from fmsm.infrastructure import yaml_store

PROJECT_ID = "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"


class FakeFusion(object):
    def __init__(self, project_id=PROJECT_ID, document=True):
        self.project_id = project_id
        self.document = document

    def active_document(self):
        return {"name": "Assembly", "data_file_id": "urn:doc"} if self.document else None

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
    def __init__(self, root=None):
        self.root = str(root) if root is not None else None

    def project_root(self, project_id):
        return self.root if project_id == PROJECT_ID else None


def _project(tmp_path):
    root = tmp_path / "repo"
    for relative in ("scenes", "assets/generated", "assets/thumbnails"):
        yaml_store.project_path(root, relative).mkdir(parents=True, exist_ok=True)
    yaml_store.write(root, "manual.yaml", new_manifest(PROJECT_ID, "Guide <Draft>", "Assembly", "urn:doc"))
    fusion = FakeFusion()
    settings = FakeSettings(root)
    scene_service = SceneService(fusion, settings)
    scene = scene_service.create_from_current({
        "title": "Install <Rail>",
        "description": "Use bracket & screw.",
        "purpose": "Show safe orientation.",
        "instructions_markdown": "1. Align\n2. Tighten",
    })["scene"]
    return root, fusion, settings, scene


def test_summary_builds_escaped_html_document_for_project_scenes(tmp_path):
    root, fusion, settings, scene = _project(tmp_path)

    result = PreviewService(fusion, settings).summary({})

    assert result["title"] == "Guide <Draft>"
    assert "<h1>Guide &lt;Draft&gt;</h1>" in result["html"]
    assert "<h1>Guide &lt;Draft&gt;</h1>" in result["body_html"]
    assert "1 scene(s)" in result["body_html"]
    assert "Install &lt;Rail&gt;" in result["body_html"]
    assert "Use bracket &amp; screw." in result["body_html"]
    assert "assets/generated/install-rail__" in result["body_html"]
    assert scene["scene_id"] in result["body_html"]


def test_summary_requires_open_project_root(tmp_path):
    fusion = FakeFusion()
    service = PreviewService(fusion, FakeSettings(None))

    with pytest.raises(ServiceError) as error:
        service.summary({})

    assert error.value.code == "PROJECT_ROOT_UNRESOLVED"
