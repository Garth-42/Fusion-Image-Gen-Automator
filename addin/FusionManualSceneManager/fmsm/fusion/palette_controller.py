"""Fusion palette adapter; this is the only initial module that imports ``adsk``."""
from __future__ import absolute_import

import json

import adsk.core

from fmsm.application.services import ProjectService
from fmsm.application.scene_service import SceneService
from fmsm.application.render_service import RenderService
from fmsm.application.preview_service import PreviewService
from fmsm.application.identity_service import IdentityService
from fmsm.application.state_service import SceneStateService
from fmsm.fusion.adapter import FusionEnvironment
from fmsm.infrastructure.settings_store import SettingsStore
from fmsm.messaging.dispatcher import MessageDispatcher
from fmsm.messaging.protocol import peek_action

PALETTE_ID = "fmsm_scene_manager_palette"
PALETTE_NAME = "Fusion Manual Scene Manager"
# ``Palettes.add`` documents exactly one local-file form: a path relative to
# the add-in root. The hand-built absolute file:// URIs used previously loaded
# the HTML document on some platforms while its subresources silently failed,
# freezing the palette on its static connecting text.
PALETTE_URL = "ui/palette.html"
PALETTE_WIDTH = 460
PALETTE_HEIGHT = 760
# How many of the page's first requests trigger a native-surface repaint nudge
# on their own. The page's opening sequence is ping, project.status,
# identity.status, so three covers the static first paint plus both DOM updates
# that follow it. Past the burst the page asks for nudges explicitly, by action.
STARTUP_REPAINT_NUDGES = 3
# The page sends this once it has updated its DOM, to ask for the window resize
# that makes the update visible. See ``nudge_native_surface``.
REPAINT_ACTION = "system.repaint"


def _log(message):
    app = adsk.core.Application.get()
    if app is not None:
        app.log("FMSM: %s" % message)


def report_startup_failure(traceback_text):
    """Log full diagnostics and show a concise, actionable error in Fusion."""
    app = adsk.core.Application.get()
    if app is not None:
        app.log("FMSM startup failed:\n%s" % traceback_text)
        ui = app.userInterface
        if ui is not None:
            ui.messageBox(
                "Fusion Manual Scene Manager could not start.\n\n"
                "Open Fusion's Text Commands window and inspect the FMSM startup log for details."
            )


class _IncomingHtmlHandler(adsk.core.HTMLEventHandler):
    def __init__(self, controller):
        super(_IncomingHtmlHandler, self).__init__()
        self._controller = controller

    def notify(self, args):
        # Respond through ``returnData`` rather than ``sendInfoToHTML``. On the
        # old (CEF) browser ``adsk.fusionSendData`` is synchronous, so the
        # palette's JavaScript thread is blocked inside that call while this
        # handler runs; a ``sendInfoToHTML`` callback issued here can never be
        # delivered and the palette hangs on its connecting state. ``returnData``
        # is handed straight back as the return value of ``fusionSendData`` and
        # works on both the old and new browsers.
        self._controller.record_palette_message()
        response = self._controller.dispatcher.dispatch(args.data)
        args.returnData = json.dumps(response)
        # Last, once this request is fully answered: resizing the palette can
        # pump the event loop, and nothing should re-enter the dispatcher while
        # it is still mid-request.
        self._controller.nudge_native_surface(
            requested=peek_action(args.data) == REPAINT_ACTION
        )


class PaletteController(object):
    def __init__(self):
        self.palette = None
        fusion = FusionEnvironment()
        project_service = ProjectService(fusion, SettingsStore())
        identity_service = IdentityService(fusion)
        state_service = SceneStateService(fusion)
        scene_service = SceneService(fusion, SettingsStore(), state_service)
        render_service = RenderService(fusion, SettingsStore())
        preview_service = PreviewService(fusion, SettingsStore())
        handlers = project_service.handlers()
        handlers.update(identity_service.handlers())
        handlers.update(state_service.handlers())
        handlers.update(scene_service.handlers())
        handlers.update(render_service.handlers())
        handlers.update(preview_service.handlers())
        self.dispatcher = MessageDispatcher(handlers)
        # Fusion only holds weak references to event handlers; anything not
        # retained here is garbage collected and its events silently stop.
        self._handlers = []
        self._saw_palette_message = False
        self._repaint_nudges_left = STARTUP_REPAINT_NUDGES
        self._logged_startup_resize_refusal = False
        self._logged_requested_resize_refusal = False

    def record_palette_message(self):
        """Leave a one-time Text Commands breadcrumb when the handshake works."""
        if not self._saw_palette_message:
            self._saw_palette_message = True
            _log("first palette message received; the page-to-add-in link works.")

    def nudge_native_surface(self, requested=False):
        """Resize the palette window a pixel and back to force it to paint.

        The Qt WebEngine palette presents its first frame before layout settles
        and then never repaints, so the window shows only the title bar and a
        fragment of the first paint until the user collapses and re-expands it.
        In-document JavaScript cannot fix this: every nudge it can reach (an
        opacity flip, a body reflow, a scroll) stays inside the page, and the
        host coalesces all of them away without invalidating the native surface.
        The workaround that does work is a *window* resize, and only the add-in
        side can perform one. Reproduce it here, around the page's requests.

        Kept to a single pixel of height, applied and immediately reverted, and
        always measured from the palette's *current* size, so a window the user
        has resized keeps the size they gave it.

        ``requested`` marks the page's own ``system.repaint`` action. Nudging on
        the startup burst alone was not enough, and the reason is an ordering
        one: this runs as a request is answered, which is *before* the page has
        received that response and updated its DOM. During startup three
        requests follow one another closely, so each nudge happens to reveal the
        update the previous response made, and the palette looks correct. A lone
        request after startup — the Refresh behind a document switch, or behind
        a scene list edited on disk — has nothing following it, so its update sat
        on an unpainted surface until a further click nudged it forward. That is
        the two-to-three-Refresh lag reported against R1.4 and R1.8.

        So the page asks for this itself, once its DOM actually changed, and a
        requested nudge is not drawn from the startup budget: it means the page
        has something new to show, which is exactly when the surface needs
        invalidating. It arrives only on a real content change, so an idle
        Refresh still moves nothing.
        """
        if not requested:
            if self._repaint_nudges_left <= 0:
                return
            self._repaint_nudges_left -= 1
        palette = self.palette
        if palette is None:
            return
        try:
            width = palette.width
            height = palette.height
            palette.setSize(width, height + 1)
            palette.setSize(width, height)
        except Exception:
            # Docked palettes own their own geometry and can refuse setSize.
            # A palette that will not resize is not a reason to fail a request.
            # Requested nudges recur for as long as the palette is used, so log
            # each kind once rather than on every content change; one line is
            # enough to diagnose a host that refuses the resize, and a flooded
            # Text Commands window buries everything else.
            if requested:
                if not self._logged_requested_resize_refusal:
                    self._logged_requested_resize_refusal = True
                    _log("palette declined the requested repaint resize.")
            elif not self._logged_startup_resize_refusal:
                self._logged_startup_resize_refusal = True
                _log("palette declined the startup repaint resize.")

    def start(self):
        app = adsk.core.Application.get()
        if app is None:
            raise RuntimeError("Fusion application is unavailable.")
        ui = app.userInterface
        if ui is None:
            raise RuntimeError("Fusion user interface is unavailable.")
        # Always build the palette from scratch. A palette left behind by an
        # earlier run (a start that failed partway, or a stop that could not
        # finish) still shows the page it loaded back then: stale markup whose
        # script exhausted its retry budget long ago, which is indistinguishable
        # from a hang. A fresh palette is the only state this code can vouch for.
        stale = ui.palettes.itemById(PALETTE_ID)
        if stale is not None:
            _log("deleting a palette left over from an earlier run.")
            stale.deleteMe()
        # Create hidden so the event handler below is attached before the page
        # can load and send its first request.
        self.palette = ui.palettes.add(
            PALETTE_ID, PALETTE_NAME, PALETTE_URL, False, True, True, PALETTE_WIDTH, PALETTE_HEIGHT
        )
        if self.palette is None:
            raise RuntimeError("Fusion did not create the FMSM palette.")
        incoming = _IncomingHtmlHandler(self)
        self.palette.incomingFromHTML.add(incoming)
        self._handlers.append(incoming)
        self.palette.isVisible = True
        _log("palette shown; waiting for the page's first ping.")

    def stop(self):
        palette = self.palette
        self.palette = None
        self._handlers = []
        if palette is None:
            return
        try:
            palette.deleteMe()
        except Exception:
            # Fusion deletes palettes itself in some situations (for example on
            # workspace switches); a second delete must not turn add-in stop
            # into an error dialog.
            _log("palette was already deleted by Fusion.")
