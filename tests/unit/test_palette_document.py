"""Invariants that keep the palette page immune to asset-loading failures.

The connecting-state hang this project debugged repeatedly came down to the
palette document rendering while a sibling file it referenced did not load.
These tests pin the structural fix: one self-contained document, reachable at
the exact relative URL the controller registers.
"""
import importlib
import sys
import types
from pathlib import Path

ADDIN_ROOT = Path(__file__).resolve().parents[2] / "addin" / "FusionManualSceneManager"
DOCUMENT = ADDIN_ROOT / "ui" / "palette.html"


def _palette_controller(monkeypatch):
    adsk_module = types.ModuleType("adsk")
    core_module = types.ModuleType("adsk.core")
    core_module.HTMLEventHandler = object
    core_module.Application = type("Application", (), {"get": staticmethod(lambda: None)})
    adsk_module.core = core_module
    monkeypatch.setitem(sys.modules, "adsk", adsk_module)
    monkeypatch.setitem(sys.modules, "adsk.core", core_module)
    sys.modules.pop("fmsm.fusion.palette_controller", None)
    return importlib.import_module("fmsm.fusion.palette_controller")


def test_document_is_fully_self_contained():
    html = DOCUMENT.read_text(encoding="utf-8")

    assert "src=" not in html, "scripts must be inline; a failed subresource load freezes the page"
    assert "<link" not in html, "styles must be inline; a failed subresource load has no visible error"
    # The split files once caused exactly that freeze; a merge must not revive them.
    assert not (DOCUMENT.parent / "app.js").exists()
    assert not (DOCUMENT.parent / "styles.css").exists()


def test_document_contains_the_handshake_and_its_failure_states():
    html = DOCUMENT.read_text(encoding="utf-8")

    assert 'id="connection-status"' in html
    assert "adsk.fusionSendData" in html
    assert "window.fusionJavaScriptHandler" in html
    # Every terminal state must be spelled out so the palette can never sit on
    # an ambiguous connecting message.
    assert "window.onerror" in html
    assert "Add-in connected." in html
    assert "Add-in did not respond" in html


def test_document_contains_the_project_workflow_controls():
    html = DOCUMENT.read_text(encoding="utf-8")

    for element_id in ("project-title", "initialize-project", "open-project", "refresh-status", "scene-list"):
        assert 'id="%s"' % element_id in html
    for action in ("project.status", "project.initialize", "project.open"):
        assert action in html


def test_controller_url_points_at_the_document(monkeypatch):
    controller_module = _palette_controller(monkeypatch)

    assert (ADDIN_ROOT / controller_module.PALETTE_URL) == DOCUMENT
    assert DOCUMENT.is_file()
