"""Guarded scene rendering use cases."""
from __future__ import absolute_import

from pathlib import Path

from fmsm.application.errors import ServiceError
from fmsm.application.services import MANIFEST_FILE
from fmsm.domain.validation import validate_manifest, validate_scene
from fmsm.infrastructure import yaml_store


class RenderService(object):
    """Apply a persisted scene, export final/thumbnail PNGs, and restore state."""

    def __init__(self, fusion, settings):
        self._fusion = fusion
        self._settings = settings

    def handlers(self):
        return {"scene.render": self.render}

    def render(self, payload):
        root, manifest = self._require_project()
        entry = self._entry(manifest, payload.get("scene_id"))
        scene = self._load_valid_scene(root, entry["file"])
        issues = self._fusion.validate_scene_references(scene)
        if issues:
            first = issues[0]
            raise ServiceError(first["code"], first["message"], {"issues": issues})
        output = scene.get("output") or {}
        final_path = yaml_store.project_path(root, output.get("image_file"))
        thumbnail_path = yaml_store.project_path(root, output.get("thumbnail_file"))
        final_path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self._fusion.capture_session_state()
        apply_result = None
        try:
            apply_result = self._fusion.apply_scene_state(scene)
            self._fusion.refresh_viewport()
            self._fusion.export_viewport_png(str(final_path), output["width_px"], output["height_px"], output.get("transparent_background", True), output.get("anti_alias", True))
            self._fusion.export_viewport_png(str(thumbnail_path), output["thumbnail_width_px"], output["thumbnail_height_px"], output.get("transparent_background", True), output.get("anti_alias", True))
        except ServiceError:
            raise
        except Exception as error:
            raise ServiceError("RENDER_FAILED", "Fusion image export failed: %s" % error)
        finally:
            try:
                self._fusion.restore_session_state(snapshot)
                self._fusion.refresh_viewport()
            except Exception as restore_error:
                raise ServiceError("STATE_RESTORE_FAILED", "Scene render finished but pre-render state could not be restored: %s" % restore_error)
        return {
            "scene_id": entry["scene_id"],
            "image_file": output.get("image_file"),
            "thumbnail_file": output.get("thumbnail_file"),
            "warnings": (apply_result or {}).get("warnings", []),
        }

    def _require_project(self):
        document = self._fusion.active_document()
        if document is None:
            raise ServiceError("NO_ACTIVE_FUSION_DESIGN", "Open the documentation assembly before rendering scenes.")
        project_id = self._fusion.read_project_id()
        if project_id is None:
            raise ServiceError("PROJECT_NOT_OPEN", "Initialize or open a manual project before rendering scenes.")
        root = self._settings.project_root(project_id)
        if root is None or not (Path(root) / MANIFEST_FILE).is_file():
            raise ServiceError("PROJECT_ROOT_UNRESOLVED", "Open the manual project folder before rendering scenes.")
        manifest = yaml_store.load(Path(root) / MANIFEST_FILE)
        issues = validate_manifest(manifest)
        if issues:
            first = issues[0]
            raise ServiceError(first.code, first.message)
        return root, manifest

    def _entry(self, manifest, scene_id):
        for entry in manifest["project"]["scenes"]:
            if entry.get("scene_id") == scene_id:
                return entry
        raise ServiceError("SCENE_NOT_FOUND", "The requested scene is not in the manifest.")

    def _load_valid_scene(self, root, relative):
        scene = yaml_store.load(yaml_store.project_path(root, relative))
        issues = validate_scene(scene)
        if issues:
            first = issues[0]
            raise ServiceError(first.code, first.message)
        return scene
