"""Machine-local mapping from immutable project IDs to local repository roots.

Absolute paths live only here, never in version-controlled project files, so a
repository stays portable and this file can be rebuilt by simply reselecting
each project's root.
"""
from __future__ import absolute_import

import datetime
import json
from pathlib import Path

from fmsm.infrastructure.atomic_write import atomic_write_text

DEFAULT_SETTINGS_PATH = Path.home() / ".fmsm" / "settings.json"


class SettingsStore(object):
    def __init__(self, path=None):
        self._path = Path(path) if path is not None else DEFAULT_SETTINGS_PATH

    def _load(self):
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # Missing or corrupt settings are recoverable: the worst outcome is
            # that the user reselects a project root once.
            return {"schema_version": 1, "projects": {}}
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != 1
            or not isinstance(data.get("projects"), dict)
        ):
            return {"schema_version": 1, "projects": {}}
        return data

    def project_root(self, project_id):
        entry = self._load()["projects"].get(project_id)
        if isinstance(entry, dict) and isinstance(entry.get("root"), str):
            return entry["root"]
        return None

    def record_project(self, project_id, root):
        data = self._load()
        data["projects"][project_id] = {
            "root": str(root),
            "last_opened": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        atomic_write_text(self._path, json.dumps(data, indent=2, sort_keys=True) + "\n")
