"""Pure-Python semantic validation for persisted manual data."""
from __future__ import absolute_import

import math
import uuid


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
