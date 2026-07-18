"""Project use cases behind the palette's ``project.*`` actions.

The service is stateless: every call re-derives the active project from the
document's stored project UUID, the machine-local settings, and the manifest
on disk, so the palette shows the same truth before and after a Fusion restart.
"""
from __future__ import absolute_import

import uuid
from pathlib import Path

from fmsm.application.errors import ServiceError
from fmsm.domain.models import new_manifest
from fmsm.domain.validation import validate_manifest
from fmsm.infrastructure import yaml_store

MANIFEST_FILE = "manual.yaml"
PROJECT_DIRECTORIES = ("scenes", "assets/generated", "assets/thumbnails")
CONFIRM_INITIALIZE = (
    "Initialize a manual project for the active document?\n\n"
    "A dedicated documentation assembly is strongly recommended: the add-in "
    "applies scene state to the open assembly while authoring and rendering, "
    "and it never saves your Fusion document automatically."
)


class ProjectService(object):
    def __init__(self, fusion, settings):
        self._fusion = fusion
        self._settings = settings

    def handlers(self):
        """Action-to-callable wiring consumed by the message dispatcher."""
        return {
            "project.status": self.status,
            "project.initialize": self.initialize,
            "project.open": self.open,
        }

    # ---- palette actions -------------------------------------------------

    def status(self, payload):
        """Describe the current document/project association without mutating."""
        document = self._fusion.active_document()
        if document is None:
            return {"document": None, "project": None, "warnings": []}
        project_id = self._fusion.read_project_id()
        if project_id is None:
            return {"document": document, "project": None, "warnings": []}
        root = self._settings.project_root(project_id)
        if root is None or not (Path(root) / MANIFEST_FILE).is_file():
            # The document names a project this machine cannot resolve yet;
            # Open Project lets the user reselect the repository root.
            issue = {
                "code": "PROJECT_ROOT_UNRESOLVED",
                "message": "This document references manual project %s, but its local folder is not known on this machine. Use Open Project to select it." % project_id,
            }
            return {"document": document, "project": None, "warnings": [issue]}
        manifest = self._load_valid_manifest(root)
        if manifest["project"]["id"] != project_id:
            raise ServiceError(
                "PROJECT_ID_MISMATCH",
                "The manifest at the recorded folder belongs to a different project than this document.",
                {"document_project_id": project_id, "manifest_project_id": manifest["project"]["id"]},
            )
        return self._summary(document, root, manifest, self._document_warnings(document, manifest))

    def initialize(self, payload):
        """Create a new manual project and associate it with the document."""
        title = (payload.get("title") or "").strip()
        if not 1 <= len(title) <= 200:
            raise ServiceError("PROJECT_TITLE_INVALID", "Project title must be 1-200 characters.")
        document = self._require_document()
        existing_project_id = self._fusion.read_project_id()
        if existing_project_id is not None and payload.get("replace_association") is not True:
            raise ServiceError(
                "PROJECT_ALREADY_ASSOCIATED",
                "This document is already associated with a manual project. Use Open Project to reselect its existing folder.",
                {"project_id": existing_project_id},
            )
        if not self._fusion.confirm(CONFIRM_INITIALIZE):
            return {"cancelled": True}
        root = self._fusion.choose_folder("Select an empty folder or Git working tree for the manual project")
        if root is None:
            return {"cancelled": True}
        if (Path(root) / MANIFEST_FILE).is_file():
            raise ServiceError(
                "PROJECT_ROOT_NOT_EMPTY",
                "The selected folder already contains manual.yaml. Use Open Project for existing projects.",
            )
        project_id = str(uuid.uuid4())
        manifest = new_manifest(project_id, title, document["name"], document["data_file_id"])
        for relative in PROJECT_DIRECTORIES:
            yaml_store.project_path(root, relative).mkdir(parents=True, exist_ok=True)
        yaml_store.write(root, MANIFEST_FILE, manifest)
        self._fusion.write_project_id(project_id)
        self._settings.record_project(project_id, root)
        return self._summary(document, root, manifest, self._document_warnings(document, manifest))

    def open(self, payload):
        """Associate the document with an existing manual project on disk."""
        document = self._require_document()
        root = self._fusion.choose_folder("Select the manual project folder containing manual.yaml")
        if root is None:
            return {"cancelled": True}
        if not (Path(root) / MANIFEST_FILE).is_file():
            raise ServiceError(
                "PROJECT_ROOT_UNRESOLVED",
                "The selected folder does not contain manual.yaml.",
            )
        manifest = self._load_valid_manifest(root)
        manifest_id = manifest["project"]["id"]
        document_id = self._fusion.read_project_id()
        if document_id is None:
            self._fusion.write_project_id(manifest_id)
        elif document_id != manifest_id:
            raise ServiceError(
                "PROJECT_ID_MISMATCH",
                "This document is already associated with a different manual project.",
                {"document_project_id": document_id, "manifest_project_id": manifest_id},
            )
        self._settings.record_project(manifest_id, root)
        return self._summary(document, root, manifest, self._document_warnings(document, manifest))

    # ---- helpers ---------------------------------------------------------

    def _require_document(self):
        document = self._fusion.active_document()
        if document is None:
            raise ServiceError(
                "NO_ACTIVE_FUSION_DESIGN",
                "Open the documentation assembly before working with a manual project.",
            )
        return document

    def _load_valid_manifest(self, root):
        try:
            manifest = yaml_store.load(Path(root) / MANIFEST_FILE)
        except yaml_store.StoreError as error:
            raise ServiceError("YAML_PARSE_FAILED", str(error))
        issues = validate_manifest(manifest)
        if issues:
            first = issues[0]
            raise ServiceError(
                first.code,
                first.message,
                {"issues": [{"code": issue.code, "message": issue.message, "path": issue.path} for issue in issues]},
            )
        return manifest

    @staticmethod
    def _document_warnings(document, manifest):
        warnings = []
        if document["data_file_id"] is None:
            warnings.append({
                "code": "DOCUMENT_ID_WEAK",
                "message": "The document has no saved cloud identity yet; save it so scenes can be matched to it reliably.",
            })
        else:
            recorded = manifest["project"]["source_document"]["data_file_id"]
            if recorded is not None and recorded != document["data_file_id"]:
                warnings.append({
                    "code": "SOURCE_DOCUMENT_MISMATCH",
                    "message": "The manifest was captured from a different source document than the one currently open.",
                })
        return warnings

    @staticmethod
    def _summary(document, root, manifest, warnings):
        project = manifest["project"]
        return {
            "document": dict(document),
            "project": {
                "id": project["id"],
                "title": project["title"],
                "root": str(root),
                "scenes": [_scene_entry_summary(root, entry) for entry in project["scenes"]],
            },
            "warnings": warnings,
        }


def _scene_entry_summary(root, entry):
    summary = dict(entry)
    path = yaml_store.project_path(root, entry["file"])
    if path.exists():
        scene = yaml_store.load(path)
        if isinstance(scene, dict) and isinstance(scene.get("scene"), dict):
            summary["title"] = scene["scene"].get("title", "")
            summary["status"] = scene["scene"].get("status", "draft")
    return summary
