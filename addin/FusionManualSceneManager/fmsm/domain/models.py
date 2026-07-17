"""Builders for persisted manual data; keys stay in documented schema order."""
from __future__ import absolute_import

RENDER_DEFAULTS = {
    "width_px": 2400,
    "height_px": 1600,
    "transparent_background": True,
    "anti_alias": True,
}


def new_manifest(project_id, title, document_name, data_file_id):
    """Build the schema-version-1 manifest for a freshly initialized project."""
    return {
        "schema_version": 1,
        "project": {
            "id": project_id,
            "title": title,
            "source_document": {
                "data_file_id": data_file_id,
                "name": document_name,
                "role": "documentation_assembly",
            },
            "render_defaults": dict(RENDER_DEFAULTS),
            "scenes": [],
        },
    }
