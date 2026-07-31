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


def test_the_page_asks_the_addin_to_repaint_once_its_dom_has_changed():
    html = DOCUMENT.read_text(encoding="utf-8")

    # Only a resize of the palette *window* invalidates this host's native
    # surface, and only the add-in can perform one. It does that as it answers a
    # request — which is before this page has handled the response and redrawn,
    # so the resize shows the DOM as it stood beforehand. Startup hid that,
    # because its three back-to-back requests each revealed the previous
    # update; a lone Refresh after a document switch did not, and needed two or
    # three clicks. The page has to ask for the resize after it redraws.
    assert "system.repaint" in html
    handle_raw = html[html.index("function handleRaw"):html.index("window.fusionJavaScriptHandler")]
    assert "requestNativeRepaintIfChanged()" in handle_raw
    # ...after the response has been applied to the DOM, not before it. (The
    # earlier call in the reserved-id branch settles the repaint's own answer.)
    assert handle_raw.index("handleRequestResponse(response)") < handle_raw.rindex("requestNativeRepaintIfChanged()")

    request_repaint = html[
        html.index("function requestNativeRepaintIfChanged"):html.index("// ---- transport")
    ]
    # Asking on every response would resize a window the user may have sized
    # themselves; the request goes out only when visible content changed.
    assert "paintedSignature" in request_repaint
    # The answer to a repaint request must not be mistaken for the answer to
    # whatever the user has in flight, so it carries a reserved id.
    assert "REPAINT_REQUEST_ID" in handle_raw
    assert "nativeRepaintPending" in request_repaint


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


def test_every_settled_request_clears_the_busy_text_it_put_up():
    html = DOCUMENT.read_text(encoding="utf-8")

    # Capture, Apply, Restore and Edit all report into a line of their own and
    # so never touched the shared feedback line, which kept their busy text —
    # "Capturing current Fusion state…", "Loading scene metadata…" — on screen
    # indefinitely and made finished operations read as hung ones. Clearing it
    # per handler would leave the next handler to forget again; the request
    # settling is what makes the busy text untrue, so it is cleared there.
    settle = html[html.index("function handleRequestResponse"):html.index("function sendRequest")]
    assert "elements.feedback.textContent = retainedFeedback;" in settle
    assert settle.index("elements.feedback.textContent") < settle.index("finish(response)")


def test_applying_a_captured_state_reports_what_it_applied():
    html = DOCUMENT.read_text(encoding="utf-8")

    # Treating everything that was not a restore as a capture printed
    # "Captured state contains undefined occurrence(s) and undefined
    # component(s)" after an apply that had worked perfectly.
    describe = html[html.index("function describeStateResult"):html.index("function stateRequest")]
    assert '"state.restore"' in describe
    assert '"state.apply_captured"' in describe
    assert "Applied captured state" in describe
    # Apply hides occurrences the capture never listed. That changes the
    # viewport, so it cannot be the part of the outcome nobody is told about.
    assert "UNLISTED_OCCURRENCE_HIDDEN" in describe


def test_the_repaint_puts_the_scroll_position_back():
    html = DOCUMENT.read_text(encoding="utf-8")

    # Hiding the body throws the box tree away, and the scroll offset with it.
    # The repaint runs after every response, so every single click bounced the
    # panel back to the top; testers had to scroll down again to reach the
    # button they had just used, on every action.
    force_repaint = html[html.index("function forceRepaint"):html.index("function scheduleRepaint")]
    assert "scrollTop" in force_repaint
    rebuild = force_repaint.index('body.style.display = "none"')
    assert force_repaint.index("scroller.scrollTop", rebuild) > rebuild, "restore the offset after the rebuild"


def test_the_repaint_signature_notices_an_image_that_changed():
    html = DOCUMENT.read_text(encoding="utf-8")

    # Comparing text alone missed a change that is purely an image: re-rendering
    # a scene updates the preview's picture while every word around it stays
    # identical, so no repaint was requested and the old picture stayed up.
    signature = html[html.index("function contentSignature"):html.index("// Only ask when")]
    assert "getElementsByTagName(\"img\")" in signature
    # Fingerprinted, not held: these sources are base64 data URIs running to
    # megabytes each.
    assert "source.length" in signature


def test_a_summary_preview_cannot_outlive_what_it_describes():
    html = DOCUMENT.read_text(encoding="utf-8")

    # Switching documents left one fixture's rendered image on screen beneath
    # another fixture's scene list, with nothing saying the picture belonged to
    # a different document. The preview is a snapshot of YAML and PNGs read at
    # one moment; it is only true of the state it was built from.
    assert "function markSummaryPreviewStale" in html
    stale = html[html.index("function markSummaryPreviewStale"):html.index("function documentContext")]
    assert "previewContext = null" in stale
    render_state = html[html.index("function renderState"):html.index("function renderIdentity")]
    assert "markSummaryPreviewStale()" in render_state
    # A mutation changes the files the preview was built from, so it goes stale
    # then too. Refresh passes "" and leaves the preview alone.
    status = html[html.index("function requestStatus"):html.index("function requestIdentityStatus")]
    assert 'if (retain !== "") { markSummaryPreviewStale(); }' in status


def test_the_scene_editor_closes_when_its_scene_is_no_longer_listed():
    html = DOCUMENT.read_text(encoding="utf-8")

    # The editor holds a scene id, not a scene. Switching documents left the
    # previous document's scene open for editing, with Save Metadata pointed at
    # a manifest that no longer contains it.
    scenes = html[html.index("function renderScenes"):html.index("function sceneIsListed")]
    assert "sceneIsListed(project, selectedSceneId)" in scenes
    assert "elements.sceneEditor.hidden = true" in scenes


def test_script_errors_name_something_and_reach_the_fusion_log():
    html = DOCUMENT.read_text(encoding="utf-8")

    # "Palette script error: Script error." named nothing, and Text Commands
    # held no matching line, so there was nothing left to investigate. Hosts
    # mask the message on a script they treat as cross-origin, but the location
    # arguments and the error object usually survive that masking.
    handler = html[html.index("window.onerror"):html.index("// ---- forced repaint")]
    for argument in ("lineNumber", "columnNumber", "error.stack"):
        assert argument in handler, argument
    # Only the add-in can write to Fusion's log, and the page has no other way in.
    assert 'transmit("system.log"' in handler
    assert "LOG_REQUEST_ID" in handler
    # Its answer must not be read as the answer to the user's in-flight request.
    handle_raw = html[html.index("function handleRaw"):html.index("window.fusionJavaScriptHandler")]
    assert "LOG_REQUEST_ID" in handle_raw


def test_linked_component_ids_are_reported_as_unsaveable():
    html = DOCUMENT.read_text(encoding="utf-8")

    # Round-4 S4.2: Fusion stores a linked component's stable ID in that
    # component's own document, which saving this assembly does not save. The
    # ID comes back missing every session and nothing said why.
    identity = html[html.index("function renderIdentity"):html.index("function describeError")]
    assert "linked_components" in identity
    assert "linked from other documents" in identity
    assert "describeLabels(" in identity
    # The click that assigns them is when the user expects saving to work.
    ensure = html[html.index('elements.ensureIds.addEventListener'):html.index('elements.repairIds.addEventListener')]
    assert "assigned.linked_components" in ensure


def test_controller_url_points_at_the_document(monkeypatch):
    controller_module = _palette_controller(monkeypatch)

    assert (ADDIN_ROOT / controller_module.PALETTE_URL) == DOCUMENT
    assert DOCUMENT.is_file()
