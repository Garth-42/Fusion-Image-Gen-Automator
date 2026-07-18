"""Scene CRUD use cases for persisted manual projects."""
from __future__ import absolute_import

import copy
import time
import uuid
from pathlib import Path

from fmsm.application.errors import ServiceError
from fmsm.application.services import MANIFEST_FILE
from fmsm.domain.filenames import scene_basename
from fmsm.domain.models import RENDER_DEFAULTS
from fmsm.domain.validation import validate_manifest, validate_scene
from fmsm.infrastructure import yaml_store

_SCENE_STATUSES = frozenset(["draft", "review", "approved", "obsolete"])
_METADATA_FIELDS = frozenset(["title", "description", "purpose", "instructions_markdown", "status", "tags"])


class SceneService(object):
    """Create, edit, duplicate, delete, reorder, and list scene YAML files."""

    def __init__(self, fusion, settings):
        self._fusion = fusion
        self._settings = settings

    def handlers(self):
        return {
            "scene.list": self.list,
            "scene.get": self.get,
            "scene.create_from_current": self.create_from_current,
            "scene.update_metadata": self.update_metadata,
            "scene.update_state": self.update_state,
            "scene.duplicate": self.duplicate,
            "scene.delete": self.delete,
            "scene.reorder": self.reorder,
        }

    def list(self, payload):
        root, manifest = self._require_project()
        return {"scenes": [self._scene_summary(root, entry) for entry in manifest["project"]["scenes"]]}

    def get(self, payload):
        root, manifest = self._require_project()
        entry = self._entry(manifest, payload.get("scene_id"))
        scene = self._load_valid_scene(root, entry["file"])
        metadata = scene["scene"]
        return {
            "scene_id": entry["scene_id"],
            "file": entry["file"],
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "purpose": metadata.get("purpose", ""),
            "instructions_markdown": metadata.get("instructions_markdown", ""),
            "status": metadata.get("status", "draft"),
            "tags": list(metadata.get("tags") or []),
            "output": dict(scene.get("output", {})),
        }

    def create_from_current(self, payload):
        root, manifest = self._require_project()
        title = self._clean_title(payload.get("title"))
        scene_id = str(uuid.uuid4())
        basename = scene_basename(title, scene_id)
        relative = "scenes/%s.yaml" % basename
        if yaml_store.project_path(root, relative).exists():
            raise ServiceError("SCENE_FILE_EXISTS", "The generated scene file already exists.")
        state = self._fusion.capture_scene_state()
        scene = self._new_scene(scene_id, basename, title, payload, state, manifest)
        self._write_scene(root, relative, scene)
        manifest["project"]["scenes"].append({"scene_id": scene_id, "file": relative})
        self._write_manifest(root, manifest)
        return {"scene": self._scene_summary(root, manifest["project"]["scenes"][-1])}

    def update_metadata(self, payload):
        root, manifest = self._require_project()
        entry = self._entry(manifest, payload.get("scene_id"))
        scene = self._load_valid_scene(root, entry["file"])
        metadata = scene["scene"]
        for key in _METADATA_FIELDS:
            if key in payload:
                self._apply_metadata(metadata, key, payload.get(key))
        self._write_scene(root, entry["file"], scene)
        return {"scene": self._scene_summary(root, entry)}

    def update_state(self, payload):
        root, manifest = self._require_project()
        entry = self._entry(manifest, payload.get("scene_id"))
        scene = self._load_valid_scene(root, entry["file"])
        state = self._fusion.capture_scene_state()
        scene["camera"] = state.get("camera")
        scene["assembly_state"] = state.get("assembly_state")
        scene["source"] = self._source_snapshot(manifest)
        self._write_scene(root, entry["file"], scene)
        return {"scene": self._scene_summary(root, entry)}

    def duplicate(self, payload):
        root, manifest = self._require_project()
        source_entry = self._entry(manifest, payload.get("scene_id"))
        source = self._load_valid_scene(root, source_entry["file"])
        scene_id = str(uuid.uuid4())
        title = self._clean_title(payload.get("title") or (source["scene"].get("title", "Scene") + " Copy"))
        basename = scene_basename(title, scene_id)
        relative = "scenes/%s.yaml" % basename
        duplicate = copy.deepcopy(source)
        duplicate["scene"]["id"] = scene_id
        duplicate["scene"]["slug"] = basename.rsplit("__", 1)[0]
        duplicate["scene"]["title"] = title
        duplicate["output"] = self._output_for_basename(basename, manifest)
        self._write_scene(root, relative, duplicate)
        index = manifest["project"]["scenes"].index(source_entry) + 1
        manifest["project"]["scenes"].insert(index, {"scene_id": scene_id, "file": relative})
        self._write_manifest(root, manifest)
        return {"scene": self._scene_summary(root, manifest["project"]["scenes"][index])}

    def delete(self, payload):
        root, manifest = self._require_project()
        entry = self._entry(manifest, payload.get("scene_id"))
        scene = self._load_valid_scene(root, entry["file"])
        warnings = []
        for relative in (entry["file"], scene.get("output", {}).get("image_file"), scene.get("output", {}).get("thumbnail_file")):
            if not relative:
                continue
            path = yaml_store.project_path(root, relative)
            if path.exists():
                path.unlink()
            elif relative != entry["file"]:
                warnings.append({"code": "SCENE_ASSET_MISSING", "message": "%s was already missing." % relative})
        manifest["project"]["scenes"].remove(entry)
        self._write_manifest(root, manifest)
        return {"deleted": payload.get("scene_id"), "warnings": warnings, "scenes": [dict(item) for item in manifest["project"]["scenes"]]}

    def reorder(self, payload):
        root, manifest = self._require_project()
        order = payload.get("scene_ids")
        current = [entry["scene_id"] for entry in manifest["project"]["scenes"]]
        if sorted(order or []) != sorted(current):
            raise ServiceError("SCENE_REORDER_INVALID", "Reorder must include each scene ID exactly once.")
        by_id = dict((entry["scene_id"], entry) for entry in manifest["project"]["scenes"])
        manifest["project"]["scenes"] = [by_id[scene_id] for scene_id in order]
        self._write_manifest(root, manifest)
        return {"scenes": [dict(item) for item in manifest["project"]["scenes"]]}

    def _require_project(self):
        document = self._fusion.active_document()
        if document is None:
            raise ServiceError("NO_ACTIVE_FUSION_DESIGN", "Open the documentation assembly before working with scenes.")
        project_id = self._fusion.read_project_id()
        if project_id is None:
            raise ServiceError("PROJECT_NOT_OPEN", "Initialize or open a manual project before working with scenes.")
        root = self._settings.project_root(project_id)
        if root is None or not (Path(root) / MANIFEST_FILE).is_file():
            raise ServiceError("PROJECT_ROOT_UNRESOLVED", "Open the manual project folder before working with scenes.")
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
        try:
            scene = yaml_store.load(yaml_store.project_path(root, relative))
        except yaml_store.StoreError as error:
            raise ServiceError("YAML_PARSE_FAILED", str(error))
        issues = validate_scene(scene)
        if issues:
            first = issues[0]
            raise ServiceError(first.code, first.message)
        return scene

    def _write_manifest(self, root, manifest):
        issues = validate_manifest(manifest)
        if issues:
            first = issues[0]
            raise ServiceError(first.code, first.message)
        yaml_store.write(root, MANIFEST_FILE, manifest)

    def _write_scene(self, root, relative, scene):
        issues = validate_scene(scene)
        if issues:
            first = issues[0]
            raise ServiceError(first.code, first.message)
        yaml_store.write(root, relative, scene)

    def _scene_summary(self, root, entry):
        scene = self._load_valid_scene(root, entry["file"])
        metadata = scene["scene"]
        return {"scene_id": entry["scene_id"], "file": entry["file"], "title": metadata.get("title", ""), "status": metadata.get("status", "draft"), "output": dict(scene.get("output", {}))}

    def _new_scene(self, scene_id, basename, title, payload, state, manifest):
        scene = {
            "schema_version": 1,
            "scene": {
                "id": scene_id,
                "slug": basename.rsplit("__", 1)[0],
                "title": title,
                "description": str(payload.get("description") or ""),
                "purpose": str(payload.get("purpose") or ""),
                "instructions_markdown": str(payload.get("instructions_markdown") or ""),
                "status": payload.get("status") or "draft",
                "tags": list(payload.get("tags") or []),
            },
            "source": self._source_snapshot(manifest),
            "camera": state.get("camera"),
            "assembly_state": state.get("assembly_state"),
            "output": self._output_for_basename(basename, manifest),
        }
        self._apply_metadata(scene["scene"], "status", scene["scene"]["status"])
        return scene

    def _source_snapshot(self, manifest):
        source = manifest["project"]["source_document"]
        return {"document_data_file_id": source.get("data_file_id"), "document_name": source.get("name"), "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "fusion_version": None}

    def _output_for_basename(self, basename, manifest):
        defaults = dict(RENDER_DEFAULTS)
        defaults.update(manifest["project"].get("render_defaults") or {})
        return {"image_file": "assets/generated/%s.png" % basename, "thumbnail_file": "assets/thumbnails/%s.png" % basename, "width_px": defaults["width_px"], "height_px": defaults["height_px"], "thumbnail_width_px": 480, "thumbnail_height_px": 320, "transparent_background": defaults["transparent_background"], "anti_alias": defaults["anti_alias"]}

    def _apply_metadata(self, metadata, key, value):
        if key == "title":
            metadata[key] = self._clean_title(value)
        elif key in ("description", "purpose", "instructions_markdown"):
            metadata[key] = str(value or "")
        elif key == "status":
            if value not in _SCENE_STATUSES:
                raise ServiceError("SCENE_STATUS_INVALID", "Scene status is not supported.")
            metadata[key] = value
        elif key == "tags":
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ServiceError("SCENE_TAGS_INVALID", "Scene tags must be strings.")
            metadata[key] = list(value)

    def _clean_title(self, title):
        title = (title or "").strip()
        if not 1 <= len(title) <= 200:
            raise ServiceError("SCENE_TITLE_INVALID", "Scene title must be 1-200 characters.")
        return title
