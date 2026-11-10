"""Scene CRUD use cases for persisted manual projects."""
from __future__ import absolute_import

import base64
import copy
import time
import uuid

from fmsm.application import project_access
from fmsm.application.errors import ServiceError
from fmsm.application.identity_service import require_capturable_ids
from fmsm.domain.filenames import scene_basename
from fmsm.domain.models import RENDER_DEFAULTS

_SCENE_STATUSES = frozenset(["draft", "review", "approved", "obsolete"])
# Thumbnails are small by construction; anything larger is not one of ours and
# is not worth pushing through the palette bridge.
_MAX_THUMBNAIL_BYTES = 2 * 1024 * 1024
_METADATA_FIELDS = frozenset(["title", "description", "purpose", "instructions_markdown", "status", "tags"])


class SceneService(object):
    """Create, edit, duplicate, delete, reorder, and list scene YAML files."""

    def __init__(self, fusion, settings, state_service=None):
        self._fusion = fusion
        self._settings = settings
        self._state_service = state_service

    def handlers(self):
        return {
            "scene.list": self.list,
            "scene.get": self.get,
            "scene.load": self.load,
            "scene.create_from_current": self.create_from_current,
            "scene.update_metadata": self.update_metadata,
            "scene.update_state": self.update_state,
            "scene.duplicate": self.duplicate,
            "scene.delete": self.delete,
            "scene.reorder": self.reorder,
            "scene.thumbnails": self.thumbnails,
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

    def load(self, payload):
        if self._state_service is None:
            raise ServiceError("SCENE_LOAD_UNAVAILABLE", "Scene loading is unavailable in this add-in session.")
        root, manifest = self._require_project()
        entry = self._entry(manifest, payload.get("scene_id"))
        scene = self._load_valid_scene(root, entry["file"])
        result = self._state_service.apply(scene)
        return {"scene": self._scene_summary(root, entry), "warnings": result.get("warnings", [])}

    def create_from_current(self, payload):
        root, manifest = self._require_project()
        title = self._clean_title(payload.get("title"))
        scene_id = str(uuid.uuid4())
        basename = scene_basename(title, scene_id)
        relative = "scenes/%s.yaml" % basename
        if project_access.safe_path(root, relative).exists():
            raise ServiceError("SCENE_FILE_EXISTS", "The generated scene file already exists.")
        require_capturable_ids(self._fusion)
        state = self._fusion.capture_scene_state()
        scene = self._new_scene(scene_id, basename, title, payload, state, manifest)
        self._write_scene(root, relative, scene)
        manifest["project"]["scenes"].append({"scene_id": scene_id, "file": relative})
        self._write_manifest_or_discard(root, manifest, relative)
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
        require_capturable_ids(self._fusion)
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
        self._write_manifest_or_discard(root, manifest, relative)
        return {"scene": self._scene_summary(root, manifest["project"]["scenes"][index])}

    def delete(self, payload):
        root, manifest = self._require_project()
        entry = self._entry(manifest, payload.get("scene_id"))
        # A scene whose YAML is broken or already gone must still be removable;
        # deleting it is how the user repairs the list. Its generated images
        # cannot be located without the YAML, so only the entry and file go.
        try:
            output = self._load_valid_scene(root, entry["file"]).get("output", {})
        except ServiceError:
            output = {}
        # Manifest first. If the files went first and the manifest write then
        # failed, the manifest would keep listing a scene with no file behind it.
        manifest["project"]["scenes"].remove(entry)
        self._write_manifest(root, manifest)
        warnings = []
        for relative in (entry["file"], output.get("image_file"), output.get("thumbnail_file")):
            if not relative:
                continue
            path = project_access.safe_path(root, relative)
            try:
                if path.exists():
                    path.unlink()
            except OSError as error:
                warnings.append({"code": "SCENE_FILE_NOT_DELETED", "message": "%s could not be deleted: %s" % (relative, error)})
        return {"deleted": payload.get("scene_id"), "warnings": warnings, "scenes": [dict(item) for item in manifest["project"]["scenes"]]}

    def reorder(self, payload):
        root, manifest = self._require_project()
        order = payload.get("scene_ids")
        current = [entry["scene_id"] for entry in manifest["project"]["scenes"]]
        # Check the shape before sorting: sorting a list of mixed types raises.
        if (
            not isinstance(order, list)
            or not all(isinstance(scene_id, str) for scene_id in order)
            or sorted(order) != sorted(current)
        ):
            raise ServiceError("SCENE_REORDER_INVALID", "Reorder must include each scene ID exactly once.")
        by_id = dict((entry["scene_id"], entry) for entry in manifest["project"]["scenes"])
        manifest["project"]["scenes"] = [by_id[scene_id] for scene_id in order]
        self._write_manifest(root, manifest)
        return {"scenes": [dict(item) for item in manifest["project"]["scenes"]]}

    def thumbnails(self, payload):
        """Return thumbnail images for the requested scenes as data URIs.

        The scene list shows thumbnails, but the palette page cannot read
        project files itself and the status response deliberately carries no
        image bytes. The page asks here for just the scenes whose thumbnail is
        new or changed, judged by the ``thumbnail_version`` in project status.
        A scene with no usable thumbnail maps to ``None``.
        """
        root, manifest = self._require_project()
        wanted = payload.get("scene_ids")
        if not isinstance(wanted, list) or not all(isinstance(scene_id, str) for scene_id in wanted):
            raise ServiceError("INVALID_PALETTE_REQUEST", "scene_ids must be a list of scene IDs.")
        wanted = set(wanted)
        thumbnails = {}
        for entry in manifest["project"]["scenes"]:
            if entry["scene_id"] in wanted:
                thumbnails[entry["scene_id"]] = self._thumbnail(root, entry)
        return {"thumbnails": thumbnails}

    def _thumbnail(self, root, entry):
        try:
            scene = self._load_valid_scene(root, entry["file"])
            path = project_access.safe_path(root, scene["output"]["thumbnail_file"])
            version = project_access.file_version(path)
            if version is None or path.stat().st_size > _MAX_THUMBNAIL_BYTES:
                return None
            data = base64.b64encode(path.read_bytes()).decode("ascii")
        except (ServiceError, OSError):
            return None
        return {"version": version, "data_uri": "data:image/png;base64," + data}

    def _require_project(self):
        return project_access.require_project(self._fusion, self._settings, "working with scenes")

    def _entry(self, manifest, scene_id):
        for entry in manifest["project"]["scenes"]:
            if entry.get("scene_id") == scene_id:
                return entry
        raise ServiceError("SCENE_NOT_FOUND", "The requested scene is not in the manifest.")

    def _load_valid_scene(self, root, relative):
        return project_access.load_scene(root, relative)

    def _write_manifest(self, root, manifest):
        project_access.write_manifest(root, manifest)

    def _write_manifest_or_discard(self, root, manifest, new_scene_file):
        """Write the manifest; on failure remove the scene file just created.

        A scene file the manifest does not list is invisible to the palette and
        would otherwise sit in the project folder forever.
        """
        try:
            self._write_manifest(root, manifest)
        except ServiceError:
            try:
                project_access.safe_path(root, new_scene_file).unlink()
            except (ServiceError, OSError):
                pass
            raise

    def _write_scene(self, root, relative, scene):
        project_access.write_scene(root, relative, scene)

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
