"""Guarded scene rendering use cases."""
from __future__ import absolute_import

from pathlib import Path

from fmsm.application.errors import ServiceError
from fmsm.application.services import MANIFEST_FILE
from fmsm.domain.validation import validate_manifest, validate_scene
from fmsm.infrastructure import atomic_write, yaml_store


class RenderService(object):
    """Apply a persisted scene, export final/thumbnail PNGs, and restore state."""

    def __init__(self, fusion, settings):
        self._fusion = fusion
        self._settings = settings

    def handlers(self):
        return {"scene.render": self.render, "scene.render_all": self.render_all}

    def render(self, payload):
        root, manifest = self._require_project()
        entry = self._entry(manifest, payload.get("scene_id"))
        records = self._fusion.identity_records()
        return self._render_entry(root, entry, records)

    def render_all(self, payload):
        root, manifest = self._require_project()
        records = self._fusion.identity_records()
        rendered = []
        warnings = []
        for entry in manifest["project"]["scenes"]:
            result = self._render_entry(root, entry, records)
            rendered.append(result)
            warnings.extend(result.get("warnings") or [])
        return {"rendered": rendered, "count": len(rendered), "warnings": warnings}

    def _render_entry(self, root, entry, records):
        scene = self._load_valid_scene(root, entry["file"])
        issues = self._fusion.validate_scene_references(scene, records)
        if issues:
            first = issues[0]
            raise ServiceError(first["code"], first["message"], {"issues": issues, "scene_id": entry["scene_id"]})
        output = scene.get("output") or {}
        final_path = yaml_store.project_path(root, output.get("image_file"))
        thumbnail_path = yaml_store.project_path(root, output.get("thumbnail_file"))
        final_path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self._fusion.capture_session_state(records)
        apply_result = None
        try:
            apply_result = self._fusion.apply_scene_state(scene, records)
            self._fusion.refresh_viewport()
            self._export_png(final_path, output["width_px"], output["height_px"], output)
            self._export_png(thumbnail_path, output["thumbnail_width_px"], output["thumbnail_height_px"], output)
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

    def _export_png(self, destination, width_px, height_px, output):
        """Export one image through a staging file, then move it into place.

        Fusion's image export can report success while writing nothing — a
        read-only output folder is the case testers hit — so the returned "ok"
        is not proof of a file. Checking the destination afterwards is not proof
        either, and that is the sharper half: re-rendering a scene whose PNG was
        already on disk found the *previous* render's file, called that a
        success, and reported the usual "Rendered …" message while nothing had
        been written (round-4 S2.4/S3.2). Only a path that cannot pre-exist can
        answer whether this export wrote anything, so export to a staging file
        and require *that* to appear.

        Moving the finished file into place afterwards also means a failed
        render leaves the previous good image untouched instead of truncating
        it, and that the destination never exists in a half-written state.
        """
        staging = atomic_write.staging_path(destination)
        try:
            self._fusion.export_viewport_png(
                str(staging), width_px, height_px,
                output.get("transparent_background", True), output.get("anti_alias", True),
            )
            self._require_written(staging, destination)
            try:
                atomic_write.commit(staging, destination)
            except OSError as error:
                raise ServiceError(
                    "RENDER_FAILED",
                    "Fusion rendered the image but it could not be written to %s: %s. "
                    "Confirm the file and its folder are writable." % (destination, error),
                )
        finally:
            atomic_write.discard(staging)

    @staticmethod
    def _require_written(staging, destination):
        try:
            written = staging.is_file() and staging.stat().st_size > 0
        except OSError:
            written = False
        if not written:
            raise ServiceError(
                "RENDER_FAILED",
                "Fusion reported success but no image was written for %s. Confirm the output folder is writable." % destination,
            )

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
