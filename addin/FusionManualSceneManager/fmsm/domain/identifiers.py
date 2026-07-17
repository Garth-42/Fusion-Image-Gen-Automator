"""Pure helpers for indexing stable Fusion occurrence and component IDs."""
from __future__ import absolute_import

import uuid


OCCURRENCE_ID = "occurrence_id"
COMPONENT_ID = "component_id"


def valid_uuid(value):
    """Return whether *value* is a non-empty UUID string."""
    try:
        uuid.UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def identity_report(records):
    """Return missing and duplicate ID records without exposing host objects.

    Each input record is expected to contain a label and optional occurrence and
    component identifiers.  Extra values (including transient Fusion handles)
    are deliberately ignored, keeping this validation executable in CPython.
    """
    occurrence_ids = {}
    component_ids = {}
    missing_occurrences = []
    missing_components = []
    for record in records:
        label = record.get("label") or "Unnamed occurrence"
        occurrence_id = record.get(OCCURRENCE_ID)
        if not valid_uuid(occurrence_id):
            missing_occurrences.append({"label": label})
        else:
            occurrence_ids.setdefault(occurrence_id, []).append({"label": label})

        # Components can occur repeatedly in an assembly.  The adapter emits
        # a component record only once per underlying component entity.
        if not record.get("component_is_primary", True):
            continue
        component_label = record.get("component_label") or label
        component_id = record.get(COMPONENT_ID)
        if not valid_uuid(component_id):
            missing_components.append({"label": component_label})
        else:
            component_ids.setdefault(component_id, []).append({"label": component_label})

    return {
        "missing_occurrences": missing_occurrences,
        "missing_components": missing_components,
        "duplicate_occurrences": _duplicates(occurrence_ids),
        "duplicate_components": _duplicates(component_ids),
    }


def _duplicates(index):
    duplicates = []
    for identifier in sorted(index):
        records = index[identifier]
        if len(records) > 1:
            duplicates.append({"id": identifier, "labels": [record["label"] for record in records]})
    return duplicates
