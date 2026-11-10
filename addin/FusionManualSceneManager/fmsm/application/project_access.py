"""Shared project resolution and file access for the application services.

Every service needs the same three things: the active document's project
folder, its validated manifest, and validated scene files. Each service used to
carry its own copy of that logic, and the copies had drifted: only one of them
turned a storage failure into a coded error, so a single hand-edited YAML file
surfaced as ``INTERNAL_ERROR`` with a traceback from most palette actions.
Keeping it here means a storage fault always reaches the palette as a stable
error code, whichever action tripped over it.
"""
from __future__ import absolute_import

from pathlib import Path

from fmsm.application.errors import ServiceError
from fmsm.domain.validation import validate_manifest, validate_scene
from fmsm.infrastructure import yaml_store

MANIFEST_FILE = "manual.yaml"


def _service_error(error):
    """Convert a storage failure into the coded error the palette displays."""
    message = str(error)
    prefix = error.code + ": "
    if message.startswith(prefix):
        message = message[len(prefix):]
    elif message == error.code:
        message = "The path leaves the manual project folder."
    return ServiceError(error.code, message)


def _issues_error(issues, extra=None):
    first = issues[0]
    details = {
        "path": first.path,
        "issues": [{"code": issue.code, "message": issue.message, "path": issue.path} for issue in issues],
    }
    details.update(extra or {})
    return ServiceError(first.code, first.message, details)


def safe_path(root, relative):
    """Resolve a project-relative path, refusing anything outside the root."""
    try:
        return yaml_store.project_path(root, relative)
    except yaml_store.StoreError as error:
        raise _service_error(error)


def load_manifest(root):
    try:
        manifest = yaml_store.load(Path(root) / MANIFEST_FILE)
    except yaml_store.StoreError as error:
        raise _service_error(error)
    issues = validate_manifest(manifest)
    if issues:
        raise _issues_error(issues)
    return manifest


def load_scene(root, relative):
    try:
        scene = yaml_store.load(yaml_store.project_path(root, relative))
    except yaml_store.StoreError as error:
        raise _service_error(error)
    issues = validate_scene(scene)
    if issues:
        raise _issues_error(issues, {"file": relative})
    return scene


def write_manifest(root, manifest):
    issues = validate_manifest(manifest)
    if issues:
        raise _issues_error(issues)
    _write(root, MANIFEST_FILE, manifest)


def write_scene(root, relative, scene):
    issues = validate_scene(scene)
    if issues:
        raise _issues_error(issues, {"file": relative})
    _write(root, relative, scene)


def _write(root, relative, data):
    try:
        yaml_store.write(root, relative, data)
    except yaml_store.StoreError as error:
        raise _service_error(error)
    except OSError as error:
        raise ServiceError("PROJECT_WRITE_FAILED", "Could not write %s: %s" % (relative, error))


def require_project(fusion, settings, activity):
    """Return ``(root, manifest)`` for the active document's manual project.

    ``activity`` finishes the sentence shown to the user, for example
    ``"rendering scenes"``.
    """
    if fusion.active_document() is None:
        raise ServiceError("NO_ACTIVE_FUSION_DESIGN", "Open the documentation assembly before %s." % activity)
    project_id = fusion.read_project_id()
    if project_id is None:
        raise ServiceError("PROJECT_NOT_OPEN", "Create or open a manual project before %s." % activity)
    root = settings.project_root(project_id)
    if root is None or not (Path(root) / MANIFEST_FILE).is_file():
        raise ServiceError("PROJECT_ROOT_UNRESOLVED", "Open the manual project file before %s." % activity)
    manifest = load_manifest(root)
    if manifest["project"]["id"] != project_id:
        raise ServiceError(
            "PROJECT_ID_MISMATCH",
            "The project file at the remembered location belongs to a different project than this document. Use Open Project File to pick the right one.",
            {"document_project_id": project_id, "manifest_project_id": manifest["project"]["id"]},
        )
    return root, manifest


def file_version(path):
    """Cheap change marker for a generated file, or ``None`` when it is absent."""
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return "%d-%d" % (stat.st_mtime_ns, stat.st_size)
