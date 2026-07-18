"""Pure-Python semantic validation for persisted manual data."""
from __future__ import absolute_import

import math
import re
import uuid

_SCENE_FILE_PATTERN = re.compile(r"^scenes/[A-Za-z0-9._/-]+\.ya?ml$")
_ASSET_FILE_PATTERN = re.compile(r"^assets/(generated|thumbnails)/[A-Za-z0-9._/-]+\.png$")
_RENDER_PIXEL_RANGE = (64, 16384)
_SCENE_STATUSES = frozenset(["draft", "review", "approved", "obsolete"])


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


def _scene_issue(code, message, path):
    return ValidationIssue(code, message, path)


def _safe_relative(value, pattern):
    return isinstance(value, str) and pattern.match(value) and ".." not in value.split("/") and not value.startswith("/")


def validate_scene(scene):
    issues = []
    if not isinstance(scene, dict):
        return [_scene_issue("SCHEMA_VERSION_UNSUPPORTED", "Scene must be a mapping.", "")]
    if "schema_version" not in scene:
        return [_scene_issue("SCHEMA_VERSION_MISSING", "Scene lacks schema_version.", "schema_version")]
    if scene.get("schema_version") != 1:
        return [_scene_issue("SCHEMA_VERSION_UNSUPPORTED", "Only schema version 1 is supported.", "schema_version")]

    scene_data = scene.get("scene")
    if not isinstance(scene_data, dict):
        issues.append(_scene_issue("SCENE_INVALID", "scene must be a mapping.", "scene"))
        scene_data = {}
    if not _is_uuid(scene_data.get("id")):
        issues.append(_scene_issue("SCENE_ID_INVALID", "Scene ID must be a UUID.", "scene.id"))
    title = scene_data.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 200:
        issues.append(_scene_issue("SCENE_TITLE_INVALID", "Scene title must be 1-200 characters.", "scene.title"))
    if scene_data.get("status") not in _SCENE_STATUSES:
        issues.append(_scene_issue("SCENE_STATUS_INVALID", "Scene status is not supported.", "scene.status"))
    for key in ("description", "purpose", "instructions_markdown"):
        if not isinstance(scene_data.get(key, ""), str):
            issues.append(_scene_issue("SCENE_INVALID", "Scene %s must be a string." % key, "scene." + key))
    tags = scene_data.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(item, str) for item in tags):
        issues.append(_scene_issue("SCENE_TAGS_INVALID", "Scene tags must be strings.", "scene.tags"))

    camera = scene.get("camera")
    if not isinstance(camera, dict):
        issues.append(_scene_issue("CAMERA_INVALID", "camera must be a mapping.", "camera"))
        camera = {}
    eye, target, up = camera.get("eye_cm"), camera.get("target_cm"), camera.get("up_vector")
    for name, value in (("eye_cm", eye), ("target_cm", target), ("up_vector", up)):
        if not _finite_numbers(value) or len(value) != 3:
            issues.append(_scene_issue("CAMERA_INVALID", "Camera %s must contain three finite values." % name, "camera." + name))
    if eye == target:
        issues.append(_scene_issue("CAMERA_INVALID", "Camera eye and target cannot match.", "camera"))
    if _finite_numbers(up) and len(up) == 3 and not any(up):
        issues.append(_scene_issue("CAMERA_INVALID", "Camera up vector cannot be zero.", "camera.up_vector"))
    camera_type = camera.get("type")
    if camera_type == "orthographic":
        extents = camera.get("extents_cm")
        if not isinstance(extents, dict) or not isinstance(extents.get("width"), (int, float)) or not isinstance(extents.get("height"), (int, float)) or not math.isfinite(extents.get("width")) or not math.isfinite(extents.get("height")) or extents.get("width") <= 0 or extents.get("height") <= 0:
            issues.append(_scene_issue("CAMERA_INVALID", "Orthographic camera extents must be positive finite values.", "camera.extents_cm"))
    elif camera_type == "perspective":
        angle = camera.get("perspective_angle_rad")
        if not isinstance(angle, (int, float)) or not math.isfinite(angle) or angle <= 0:
            issues.append(_scene_issue("CAMERA_INVALID", "Perspective camera angle must be a positive finite value.", "camera.perspective_angle_rad"))
    else:
        issues.append(_scene_issue("CAMERA_INVALID", "Camera type must be orthographic or perspective.", "camera.type"))

    assembly = scene.get("assembly_state")
    if not isinstance(assembly, dict):
        issues.append(_scene_issue("ASSEMBLY_STATE_INVALID", "assembly_state must be a mapping.", "assembly_state"))
        assembly = {}
    occurrences = assembly.get("occurrences", [])
    if not isinstance(occurrences, list):
        issues.append(_scene_issue("ASSEMBLY_STATE_INVALID", "occurrences must be a list.", "assembly_state.occurrences"))
        occurrences = []
    for index, occurrence in enumerate(occurrences):
        if not isinstance(occurrence, dict):
            issues.append(_scene_issue("ASSEMBLY_STATE_INVALID", "Occurrence state must be a mapping.", "assembly_state.occurrences.%d" % index))
            continue
        matrix = occurrence.get("transform_matrix_cm")
        if not _finite_numbers(matrix) or len(matrix) != 16:
            issues.append(_scene_issue("TRANSFORM_INVALID", "Occurrence transform must contain sixteen finite values.", "assembly_state.occurrences.%d" % index))
        if not _is_uuid(occurrence.get("occurrence_id")):
            issues.append(_scene_issue("OCCURRENCE_ID_INVALID", "Occurrence ID must be a UUID.", "assembly_state.occurrences.%d" % index))
        if not isinstance(occurrence.get("visible"), bool):
            issues.append(_scene_issue("VISIBILITY_INVALID", "Occurrence visible must be boolean.", "assembly_state.occurrences.%d.visible" % index))

    components = assembly.get("components", [])
    if not isinstance(components, list):
        issues.append(_scene_issue("ASSEMBLY_STATE_INVALID", "components must be a list.", "assembly_state.components"))
        components = []
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            issues.append(_scene_issue("ASSEMBLY_STATE_INVALID", "Component state must be a mapping.", "assembly_state.components.%d" % index))
            continue
        if not _is_uuid(component.get("component_id")):
            issues.append(_scene_issue("COMPONENT_ID_INVALID", "Component ID must be a UUID.", "assembly_state.components.%d" % index))
        opacity = component.get("opacity")
        if not isinstance(opacity, (int, float)) or isinstance(opacity, bool) or not math.isfinite(opacity) or opacity < 0 or opacity > 1:
            issues.append(_scene_issue("OPACITY_INVALID", "Component opacity must be between 0 and 1.", "assembly_state.components.%d.opacity" % index))

    output = scene.get("output")
    if not isinstance(output, dict):
        issues.append(_scene_issue("OUTPUT_INVALID", "output must be a mapping.", "output"))
        output = {}
    for key in ("image_file", "thumbnail_file"):
        if not _safe_relative(output.get(key), _ASSET_FILE_PATTERN):
            issues.append(_scene_issue("OUTPUT_PATH_UNSAFE", "Output paths must stay under assets/generated or assets/thumbnails.", "output." + key))
    minimum, maximum = _RENDER_PIXEL_RANGE
    for key in ("width_px", "height_px", "thumbnail_width_px", "thumbnail_height_px"):
        value = output.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            issues.append(_scene_issue("OUTPUT_INVALID", "Output %s must be an integer between %d and %d." % (key, minimum, maximum), "output." + key))
    for key in ("transparent_background", "anti_alias"):
        if not isinstance(output.get(key), bool):
            issues.append(_scene_issue("OUTPUT_INVALID", "Output %s must be boolean." % key, "output." + key))
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
    seen_files = set()
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
        if not _safe_relative(file_path, _SCENE_FILE_PATTERN):
            issues.append(_manifest_issue("Scene entry file must be a scenes/*.yaml project-relative path.", path + ".file"))
        elif file_path in seen_files:
            issues.append(_manifest_issue("Scene entry file is duplicated.", path + ".file"))
        else:
            seen_files.add(file_path)


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
