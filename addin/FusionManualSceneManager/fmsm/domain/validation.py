"""Pure-Python semantic validation for persisted manual data."""
from __future__ import absolute_import

import math
import re
import uuid

_SCENE_FILE_PATTERN = re.compile(r"^scenes/[A-Za-z0-9._/-]+\.ya?ml$")
_RENDER_PIXEL_RANGE = (64, 16384)


class ValidationIssue(object):
    def __init__(self, code, message, path):
        self.code = code
        self.message = message
        self.path = path


def _is_uuid(value):
    try:
        uuid.UUID(value)
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def _finite_numbers(values):
    return isinstance(values, list) and all(isinstance(value, (int, float)) and math.isfinite(value) for value in values)


def validate_scene(scene):
    issues = []
    if not isinstance(scene, dict) or scene.get("schema_version") != 1:
        return [ValidationIssue("SCHEMA_VERSION_UNSUPPORTED", "Only schema version 1 is supported.", "schema_version")]
    scene_data = scene.get("scene", {})
    if not _is_uuid(scene_data.get("id")):
        issues.append(ValidationIssue("SCENE_ID_INVALID", "Scene ID must be a UUID.", "scene.id"))
    camera = scene.get("camera", {})
    eye, target, up = camera.get("eye_cm"), camera.get("target_cm"), camera.get("up_vector")
    for name, value in (("eye_cm", eye), ("target_cm", target), ("up_vector", up)):
        if not _finite_numbers(value) or len(value) != 3:
            issues.append(ValidationIssue("CAMERA_INVALID", "Camera %s must contain three finite values." % name, "camera." + name))
    if eye == target:
        issues.append(ValidationIssue("CAMERA_INVALID", "Camera eye and target cannot match.", "camera"))
    if _finite_numbers(up) and len(up) == 3 and not any(up):
        issues.append(ValidationIssue("CAMERA_INVALID", "Camera up vector cannot be zero.", "camera.up_vector"))
    for index, occurrence in enumerate(scene.get("assembly_state", {}).get("occurrences", [])):
        matrix = occurrence.get("transform_matrix_cm")
        if not _finite_numbers(matrix) or len(matrix) != 16:
            issues.append(ValidationIssue("TRANSFORM_INVALID", "Occurrence transform must contain sixteen finite values.", "assembly_state.occurrences.%d" % index))
        if not _is_uuid(occurrence.get("occurrence_id")):
            issues.append(ValidationIssue("OCCURRENCE_ID_INVALID", "Occurrence ID must be a UUID.", "assembly_state.occurrences.%d" % index))
    return issues


def _manifest_issue(message, path):
    return ValidationIssue("MANIFEST_INVALID", message, path)


def _validate_source_document(source, issues):
    if not isinstance(source, dict):
        issues.append(_manifest_issue("source_document must be a mapping.", "project.source_document"))
        return
    if source.get("role") != "documentation_assembly":
        issues.append(_manifest_issue("source_document role must be documentation_assembly.", "project.source_document.role"))
    if not isinstance(source.get("name"), str) or not source.get("name"):
        issues.append(_manifest_issue("source_document name must be a non-empty string.", "project.source_document.name"))
    data_file_id = source.get("data_file_id")
    if data_file_id is not None and not isinstance(data_file_id, str):
        issues.append(_manifest_issue("source_document data_file_id must be a string or null.", "project.source_document.data_file_id"))


def _validate_render_defaults(render, issues):
    if not isinstance(render, dict):
        issues.append(_manifest_issue("render_defaults must be a mapping.", "project.render_defaults"))
        return
    minimum, maximum = _RENDER_PIXEL_RANGE
    for key in ("width_px", "height_px"):
        value = render.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            issues.append(_manifest_issue("render_defaults %s must be an integer between %d and %d." % (key, minimum, maximum), "project.render_defaults." + key))
    for key in ("transparent_background", "anti_alias"):
        if not isinstance(render.get(key), bool):
            issues.append(_manifest_issue("render_defaults %s must be a boolean." % key, "project.render_defaults." + key))


def _validate_manifest_scenes(scenes, issues):
    if not isinstance(scenes, list):
        issues.append(_manifest_issue("scenes must be a list.", "project.scenes"))
        return
    seen_ids = set()
    for index, entry in enumerate(scenes):
        path = "project.scenes.%d" % index
        if not isinstance(entry, dict):
            issues.append(_manifest_issue("Scene entry must be a mapping.", path))
            continue
        scene_id = entry.get("scene_id")
        if not _is_uuid(scene_id):
            issues.append(_manifest_issue("Scene entry scene_id must be a UUID.", path + ".scene_id"))
        elif scene_id in seen_ids:
            issues.append(_manifest_issue("Scene entry scene_id is duplicated.", path + ".scene_id"))
        else:
            seen_ids.add(scene_id)
        file_path = entry.get("file")
        if not isinstance(file_path, str) or not _SCENE_FILE_PATTERN.match(file_path) or ".." in file_path.split("/"):
            issues.append(_manifest_issue("Scene entry file must be a scenes/*.yaml project-relative path.", path + ".file"))


def validate_manifest(manifest):
    """Check a parsed manual.yaml against the documented schema-version-1 shape."""
    if not isinstance(manifest, dict):
        return [_manifest_issue("Manifest must be a mapping.", "")]
    if "schema_version" not in manifest:
        return [ValidationIssue("SCHEMA_VERSION_MISSING", "Manifest lacks schema_version.", "schema_version")]
    if manifest.get("schema_version") != 1:
        return [ValidationIssue("SCHEMA_VERSION_UNSUPPORTED", "Only schema version 1 is supported.", "schema_version")]
    project = manifest.get("project")
    if not isinstance(project, dict):
        return [_manifest_issue("project must be a mapping.", "project")]
    issues = []
    if not _is_uuid(project.get("id")):
        issues.append(_manifest_issue("Project id must be a UUID.", "project.id"))
    title = project.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 200:
        issues.append(_manifest_issue("Project title must be 1-200 characters.", "project.title"))
    _validate_source_document(project.get("source_document"), issues)
    _validate_render_defaults(project.get("render_defaults"), issues)
    _validate_manifest_scenes(project.get("scenes"), issues)
    return issues
