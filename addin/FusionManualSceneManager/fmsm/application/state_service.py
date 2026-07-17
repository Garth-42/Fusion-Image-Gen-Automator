"""Guarded scene-state application independent of Fusion API objects."""
from __future__ import absolute_import

from fmsm.application.errors import ServiceError
from fmsm.domain.validation import validate_scene


class SessionStateGuard(object):
    """Capture state once and restore it even when scene application fails."""

    def __init__(self, fusion):
        self._fusion = fusion
        self._snapshot = None

    def apply(self, scene):
        if self._snapshot is None:
            self._snapshot = self._fusion.capture_session_state()
        try:
            result = self._fusion.apply_scene_state(scene)
            self._fusion.refresh_viewport()
            return result
        except Exception:
            self._restore_or_raise()
            raise

    def restore(self):
        if self._snapshot is None:
            return False
        self._restore_or_raise()
        return True

    def _restore_or_raise(self):
        snapshot = self._snapshot
        self._snapshot = None
        try:
            self._fusion.restore_session_state(snapshot)
            self._fusion.refresh_viewport()
        except Exception:
            raise ServiceError("STATE_RESTORE_FAILED", "Fusion could not fully restore the pre-scene state.")


class SceneStateService(object):
    """Validate a complete scene before delegating state mutation to Fusion."""

    def __init__(self, fusion):
        self._fusion = fusion
        self._guard = SessionStateGuard(fusion)

    def apply(self, scene):
        issues = validate_scene(scene)
        if issues:
            issue = issues[0]
            raise ServiceError(issue.code, issue.message, {"path": issue.path})
        references = self._fusion.validate_scene_references(scene)
        if references:
            raise ServiceError(references[0]["code"], references[0]["message"], references[0])
        return self._guard.apply(scene)

    def restore(self):
        return {"restored": self._guard.restore()}
