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

    for element_id in ("project-title", "initialize-project", "open-project", "refresh-status", "scene-list", "render-all-scenes", "preview-summary", "summary-preview-panel", "summary-preview-content", "close-summary-preview", "update-scene-state"):
        assert 'id="%s"' % element_id in html
    for action in ("project.status", "project.initialize", "project.open", "preview.summary", "scene.load", "scene.render_all", "scene.update_state"):
        assert action in html
    assert "PROJECT_ALREADY_ASSOCIATED" in html
    assert "replace_association" in html
    assert "window.open" not in html
    assert "srcdoc" not in html
    assert "innerHTML" in html


def test_document_contains_identity_management_controls():
    html = DOCUMENT.read_text(encoding="utf-8")

    for element_id in ("identity-panel", "ensure-ids", "repair-ids"):
        assert 'id="%s"' % element_id in html
    for action in ("identity.status", "identity.ensure_ids", "identity.repair_duplicates"):
        assert action in html


def test_document_contains_state_preview_controls():
    html = DOCUMENT.read_text(encoding="utf-8")

    for action in ("state.capture_current", "state.apply_captured", "state.restore"):
        assert action in html


def test_document_forces_repaints_so_it_cannot_stay_blank():
    html = DOCUMENT.read_text(encoding="utf-8")

    # A host that presents its first frame before layout settles and never
    # repaints on DOM mutation leaves the palette blank until an unrelated
    # resize. The page must invalidate its own surface instead of relying on
    # the user to nudge it.
    assert "function forceRepaint" in html
    assert "function scheduleRepaint" in html
    assert "requestAnimationFrame" in html
    # A compositor-only nudge (opacity alone) is coalesced away by the Qt
    # WebEngine host without invalidating the native surface, so the repaint
    # must also force a real reflow — the same thing collapsing/expanding a
    # panel does. Pin that layout nudge so it cannot regress to opacity-only.
    force_repaint = html[html.index("function forceRepaint"):html.index("function scheduleRepaint")]
    assert "marginBottom" in force_repaint
    assert "offsetHeight" in force_repaint
    # Opacity plus a reflow still left the palette blank in Fusion, so the
    # strongest in-document invalidation — throwing the box tree away and
    # rebuilding it — has to be there too.
    assert 'body.style.display = "none"' in force_repaint
    # ...but not while the user is typing, because hiding the body drops focus
    # and the caret with it.
    assert "isEditing()" in force_repaint
    # The repaint must fire after every response so a document switch cannot
    # leave a stale document line on screen even after Refresh.
    handle_raw = html[html.index("function handleRaw"):html.index("window.fusionJavaScriptHandler")]
    assert "scheduleRepaint()" in handle_raw


def test_startup_repaint_burst_outlasts_the_observed_blank_window():
    html = DOCUMENT.read_text(encoding="utf-8")

    # Testers measured the palette staying blank past seven seconds. A burst
    # that stops at one second cannot cover that, so pin the tail of the
    # schedule rather than only its existence.
    burst = html[html.index("].forEach(function (delay) {") - 200:html.index("].forEach(function (delay) {")]
    delays = [int(value) for value in burst[burst.rindex("[") + 1:].split(",")]
    assert delays[0] == 0, "the first nudge must not wait for a timer"
    assert max(delays) >= 7500, "the burst must outlast the blank window testers measured"
    assert delays == sorted(delays)


def test_identity_status_clears_the_shared_feedback_line():
    html = DOCUMENT.read_text(encoding="utf-8")

    body = html[html.index("function requestIdentityStatus"):html.index("function handleMutationResponse")]
    # The busy text is shown while the background check runs; it must be cleared
    # when the check settles so it does not read as a stuck operation. It is the
    # retained message that replaces it, which is the empty string unless a
    # mutation just finished and asked for its outcome to survive this refresh.
    assert "Checking stable IDs" in body
    assert "elements.feedback.textContent = retainedFeedback" in body
    # A background refresh must not wipe the message it was fired to preserve.
    assert '"Checking stable IDs…", true' in body


def test_mutation_outcomes_survive_the_refresh_fired_behind_them():
    html = DOCUMENT.read_text(encoding="utf-8")

    # A render that succeeded reported nothing: renderScene set its message and
    # then called requestStatus, whose own success path blanked the same line
    # microseconds later. Every mutation that refreshes behind itself must hand
    # its message to requestStatus instead of racing it.
    for message in (
        '"Rendered " + response.result.image_file',
        '"Rendered " + response.result.count',
        '"Scene list updated."',
        '"Scene metadata saved."',
        '"Scene graphics updated from current Fusion state."',
        '"Scene order updated."',
    ):
        assert "requestStatus(" + message in html, message

    status = html[html.index("function requestStatus"):html.index("function requestIdentityStatus")]
    assert "elements.feedback.textContent = retainedFeedback" in status
    assert '"Checking project association…", true' in status
    # Refresh is a user action, so it starts from a clean line rather than
    # re-showing the outcome of something the user did earlier.
    assert 'elements.refresh.addEventListener("click", function () { requestStatus(""); });' in html
    # Any request that is not one of those two background refreshes drops the
    # retained message, so it can never outlive the action it describes.
    send_request = html[html.index("function sendRequest"):html.index("function setBusy")]
    assert 'if (!isBackgroundRefresh) { retainedFeedback = ""; }' in send_request


def test_controller_url_points_at_the_document(monkeypatch):
    controller_module = _palette_controller(monkeypatch)

    assert (ADDIN_ROOT / controller_module.PALETTE_URL) == DOCUMENT
    assert DOCUMENT.is_file()
