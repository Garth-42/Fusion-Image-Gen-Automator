"""Project use cases behind the palette's ``project.*`` actions.

The service is stateless: every call re-derives the active project from the
document's stored project UUID, the machine-local settings, and the manifest
on disk, so the palette shows the same truth before and after a Fusion restart.
"""
from __future__ import absolute_import

import uuid
from pathlib import Path

from fmsm.application import project_access
from fmsm.application.errors import ServiceError
from fmsm.application.project_access import MANIFEST_FILE
from fmsm.domain.models import new_manifest
from fmsm.infrastructure import yaml_store
from fmsm.infrastructure.settings_store import SettingsError

PROJECT_FILE_FILTER = "Manual project files (*.yaml)"
PROJECT_DIRECTORIES = ("scenes", "assets/generated", "assets/thumbnails")
CONFIRM_INITIALIZE = (
    "Initialize a manual project for the active document?\n\n"
    "A dedicated documentation assembly is strongly recommended: the add-in "
    "applies scene state to the open assembly while authoring and rendering, "
    "and it never saves your Fusion document automatically."
)
CONFIRM_RELINK = (
    "This document is already linked to a different manual project.\n\n"
    "Link it to \"%s\" instead? Scenes in that project only replay correctly "
    "if they were captured from this assembly."
)
_DESCRIPTION_EXCERPT_LENGTH = 140


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
            return self._without_project(document, [])
        root = self._settings.project_root(project_id)
        if root is None or not (Path(root) / MANIFEST_FILE).is_file():
            # The document names a project this machine cannot resolve yet;
            # Open Project File lets the user point at it again.
            issue = {
                "code": "PROJECT_ROOT_UNRESOLVED",
                "message": "This document is linked to a manual project whose file cannot be found on this computer. Use Open Project File to locate its manual.yaml.",
            }
            return self._without_project(document, [issue])
        manifest = project_access.load_manifest(root)
        if manifest["project"]["id"] != project_id:
            raise ServiceError(
                "PROJECT_ID_MISMATCH",
                "The project file at the remembered location belongs to a different project than this document. Use Open Project File to pick the right one.",
                {"document_project_id": project_id, "manifest_project_id": manifest["project"]["id"]},
            )
        return self._summary(document, root, manifest, self._document_warnings(document, manifest))

    def _without_project(self, document, warnings):
        """Status for a document with no usable project yet.

        ``remembered_project_file`` is only present when this computer remembers
        a project file for the document and that file still exists. It covers
        the common trap where the link was never saved into the Fusion document
        (the add-in never saves it for the user), so the next session starts
        unlinked even though the project is exactly where it was.
        """
        result = {"document": document, "project": None, "warnings": warnings}
        remembered = self._settings.document_project_file(document["data_file_id"])
        if remembered is not None and Path(remembered).is_file():
            result["remembered_project_file"] = remembered
        return result

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
        root = self._fusion.choose_folder(
            "Select an empty folder or Git working tree for the new manual project",
            self._default_directory(document),
        )
        if root is None:
            return {"cancelled": True}
        if (Path(root) / MANIFEST_FILE).is_file():
            raise ServiceError(
                "PROJECT_ROOT_NOT_EMPTY",
                "The selected folder already contains manual.yaml. Use Open Project File for existing projects.",
            )
        project_id = str(uuid.uuid4())
        manifest = new_manifest(project_id, title, document["name"], document["data_file_id"])
        try:
            for relative in PROJECT_DIRECTORIES:
                yaml_store.project_path(root, relative).mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise ServiceError("PROJECT_WRITE_FAILED", "Could not create the project folders: %s" % error)
        project_access.write_manifest(root, manifest)
        self._fusion.write_project_id(project_id)
        self._remember(project_id, root, document)
        return self._summary(document, root, manifest, self._document_warnings(document, manifest))

    def open(self, payload):
        """Link the document to an existing manual project file on disk.

        A project is opened by choosing its ``manual.yaml``; the folder that
        file sits in is the project folder. The dialog starts wherever this CAD
        document's project was last opened from. ``use_remembered`` skips the
        dialog and reopens that remembered file directly; the path comes from
        this computer's settings, never from the palette.
        """
        document = self._require_document()
        if payload.get("use_remembered") is True:
            project_file = self._settings.document_project_file(document["data_file_id"])
            if project_file is None or not Path(project_file).is_file():
                raise ServiceError(
                    "PROJECT_FILE_NOT_FOUND",
                    "The project file remembered for this document is no longer there. Use Open Project File to locate it.",
                )
        else:
            project_file = self._fusion.choose_file(
                "Open the manual project file (manual.yaml)",
                PROJECT_FILE_FILTER,
                self._default_directory(document),
                MANIFEST_FILE,
            )
            if project_file is None:
                return {"cancelled": True}
        project_file = Path(project_file)
        if project_file.name != MANIFEST_FILE:
            raise ServiceError(
                "PROJECT_FILE_INVALID",
                "\"%s\" is not a manual project file. Choose the file named manual.yaml in the project folder." % project_file.name,
            )
        if not project_file.is_file():
            raise ServiceError("PROJECT_FILE_NOT_FOUND", "The selected project file does not exist.")
        root = str(project_file.parent)
        manifest = project_access.load_manifest(root)
        manifest_id = manifest["project"]["id"]
        document_id = self._fusion.read_project_id()
        if document_id != manifest_id:
            # A document that already names another project is re-linked only
            # on an explicit yes; a fresh document needs no question.
            if document_id is not None and not self._fusion.confirm(CONFIRM_RELINK % manifest["project"]["title"]):
                return {"cancelled": True}
            self._fusion.write_project_id(manifest_id)
        self._remember(manifest_id, root, document)
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

    def _remember(self, project_id, root, document):
        try:
            self._settings.record_project(
                project_id, root, document["data_file_id"], str(Path(root) / MANIFEST_FILE)
            )
        except SettingsError as error:
            raise ServiceError("SETTINGS_WRITE_FAILED", str(error))

    def _default_directory(self, document):
        """Pick the folder a project dialog should start in for this document.

        Prefer the project file last used with this exact CAD document, then
        the folder of the project the document is linked to, then wherever a
        project was opened last. Stale entries are skipped, not reported: this
        is only a convenience starting point.
        """
        candidates = [self._settings.document_project_file(document["data_file_id"])]
        project_id = self._fusion.read_project_id()
        if project_id is not None:
            root = self._settings.project_root(project_id)
            if root is not None:
                candidates.append(str(Path(root) / MANIFEST_FILE))
        candidates.append(self._settings.last_project_file())
        for candidate in candidates:
            if candidate and Path(candidate).parent.is_dir():
                return str(Path(candidate).parent)
        return None

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
                "file": str(Path(root) / MANIFEST_FILE),
                "scenes": [_scene_entry_summary(root, entry) for entry in project["scenes"]],
            },
            "warnings": warnings,
        }


def _scene_entry_summary(root, entry):
    """Describe one manifest entry for the scene list.

    Deliberately forgiving: a scene file that is missing or unreadable becomes
    a row carrying an ``error`` instead of failing the whole status request,
    because the list is also where the user goes to delete a broken scene.
    Thumbnail bytes are not included; ``thumbnail_version`` lets the palette
    fetch only the thumbnails that are new or changed.
    """
    summary = dict(entry)
    try:
        path = yaml_store.project_path(root, entry["file"])
        if not path.exists():
            summary["error"] = "The scene file is missing."
            return summary
        scene = yaml_store.load(path)
    except yaml_store.StoreError as error:
        summary["error"] = "The scene file cannot be read: %s" % error
        return summary
    metadata = scene.get("scene")
    if not isinstance(metadata, dict):
        summary["error"] = "The scene file has no scene section."
        return summary
    summary["title"] = _text(metadata.get("title"))
    summary["status"] = _text(metadata.get("status")) or "draft"
    description = " ".join(_text(metadata.get("description")).split())
    if len(description) > _DESCRIPTION_EXCERPT_LENGTH:
        description = description[:_DESCRIPTION_EXCERPT_LENGTH - 1].rstrip() + "\u2026"
    summary["description"] = description
    summary["thumbnail_version"] = None
    summary["rendered"] = False
    output = scene.get("output")
    if isinstance(output, dict):
        summary["thumbnail_version"] = _asset_version(root, output.get("thumbnail_file"))
        summary["rendered"] = _asset_version(root, output.get("image_file")) is not None
    return summary


def _text(value):
    return value if isinstance(value, str) else ""


def _asset_version(root, relative):
    if not isinstance(relative, str) or not relative:
        return None
    try:
        return project_access.file_version(yaml_store.project_path(root, relative))
    except yaml_store.StoreError:
        return None
