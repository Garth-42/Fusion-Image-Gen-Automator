"""Machine-local memory of where each manual project lives on this computer.

Two lookups are kept:

- ``projects`` maps an immutable project ID to its local folder, which is how
  a document that names a project finds its files again.
- ``documents`` maps a CAD document's stable cloud ID to the project file last
  opened with it, so the file dialog for that document starts where its
  project is, and the palette can offer to reopen it directly.

Absolute paths live only here, never in version-controlled project files, so a
repository stays portable and this file can be rebuilt by simply reopening
each project file.
"""
from __future__ import absolute_import

import datetime
import json
from pathlib import Path

from fmsm.infrastructure.atomic_write import atomic_write_text

DEFAULT_SETTINGS_PATH = Path.home() / ".fmsm" / "settings.json"


def _empty():
    return {"schema_version": 1, "projects": {}, "documents": {}}


class SettingsStore(object):
    def __init__(self, path=None):
        self._path = Path(path) if path is not None else DEFAULT_SETTINGS_PATH

    def _load(self):
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # Missing or corrupt settings are recoverable: the worst outcome is
            # that the user reopens a project file once.
            return _empty()
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != 1
            or not isinstance(data.get("projects"), dict)
        ):
            return _empty()
        # Files written before per-document memory existed have no such key.
        if not isinstance(data.get("documents"), dict):
            data["documents"] = {}
        return data

    def project_root(self, project_id):
        entry = self._load()["projects"].get(project_id)
        if isinstance(entry, dict) and isinstance(entry.get("root"), str):
            return entry["root"]
        return None

    def document_project_file(self, document_id):
        """Return the project file last used with this CAD document, if any."""
        if not document_id:
            return None
        entry = self._load()["documents"].get(document_id)
        if isinstance(entry, dict) and isinstance(entry.get("project_file"), str):
            return entry["project_file"]
        return None

    def last_project_file(self):
        """Return the project file opened most recently with any document."""
        value = self._load().get("last_project_file")
        return value if isinstance(value, str) else None

    def record_project(self, project_id, root, document_id=None, project_file=None):
        """Remember a project's folder and, when given, which document used it.

        ``document_id`` is the document's stable cloud ID; unsaved documents
        have none and are simply not remembered individually.
        """
        data = self._load()
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        data["projects"][project_id] = {"root": str(root), "last_opened": now}
        if project_file is not None:
            data["last_project_file"] = str(project_file)
            if document_id:
                data["documents"][document_id] = {
                    "project_file": str(project_file),
                    "project_id": project_id,
                    "last_opened": now,
                }
        try:
            atomic_write_text(self._path, json.dumps(data, indent=2, sort_keys=True) + "\n")
        except OSError as error:
            raise SettingsError("Could not save add-in settings to %s: %s" % (self._path, error))


class SettingsError(Exception):
    pass
