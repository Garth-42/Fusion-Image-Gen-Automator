"""Interfaces the application layer depends on; ``fmsm.fusion`` implements them.

Application services must stay executable without Fusion, so everything they
need from the host is expressed here and injected explicitly.
"""
from __future__ import absolute_import


class FusionEnvironmentPort(object):
    """The Fusion-facing operations project use cases require."""

    def active_document(self):
        """Return ``{"name": str, "data_file_id": str or None}`` or ``None``.

        ``data_file_id`` is ``None`` for documents that were never saved; the
        service reports that as a weak-identity warning rather than an error.
        """
        raise NotImplementedError

    def confirm(self, message):
        """Show a yes/no question and return the user's choice as a bool."""
        raise NotImplementedError

    def choose_folder(self, title):
        """Show a folder picker; return an absolute path, or ``None`` on cancel."""
        raise NotImplementedError

    def read_project_id(self):
        """Return the project UUID stored on the active document, or ``None``."""
        raise NotImplementedError

    def write_project_id(self, project_id):
        """Persist the project UUID on the active document's attributes."""
        raise NotImplementedError

    def identity_records(self):
        """Return transient handles and diagnostic data for managed entities."""
        raise NotImplementedError

    def write_occurrence_id(self, occurrence_handle, occurrence_id):
        """Write a UUID attribute to one managed occurrence."""
        raise NotImplementedError

    def write_component_id(self, component_handle, component_id):
        """Write a UUID attribute to one managed component."""
        raise NotImplementedError

    def capture_session_state(self, records=None):
        """Capture camera and managed assembly state for later restoration."""
        raise NotImplementedError

    def capture_scene_state(self):
        """Capture a serializable camera and assembly-state payload."""
        raise NotImplementedError

    def validate_scene_references(self, scene, records=None):
        """Return blocking reference diagnostics without mutating Fusion."""
        raise NotImplementedError

    def apply_scene_state(self, scene, records=None):
        """Apply a previously validated scene state on the Fusion UI thread."""
        raise NotImplementedError

    def restore_session_state(self, snapshot):
        """Restore a snapshot captured by :meth:`capture_session_state`."""
        raise NotImplementedError

    def refresh_viewport(self):
        """Refresh Fusion's viewport after applying or restoring state."""
        raise NotImplementedError

    def export_viewport_png(self, path, width_px, height_px, transparent_background, anti_alias):
        """Export the current viewport to a PNG at ``path``."""
        raise NotImplementedError
