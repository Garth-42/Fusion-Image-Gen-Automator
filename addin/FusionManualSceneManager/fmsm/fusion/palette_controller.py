"""Fusion palette adapter; this is the only initial module that imports ``adsk``."""
from __future__ import absolute_import

import json

import adsk.core

from fmsm.application.services import ProjectService
from fmsm.application.scene_service import SceneService
from fmsm.application.render_service import RenderService
from fmsm.application.identity_service import IdentityService
from fmsm.application.state_service import SceneStateService
from fmsm.fusion.adapter import FusionEnvironment
from fmsm.infrastructure.settings_store import SettingsStore
from fmsm.messaging.dispatcher import MessageDispatcher

PALETTE_ID = "fmsm_scene_manager_palette"
PALETTE_NAME = "Fusion Manual Scene Manager"
# ``Palettes.add`` documents exactly one local-file form: a path relative to
# the add-in root. The hand-built absolute file:// URIs used previously loaded
# the HTML document on some platforms while its subresources silently failed,
# freezing the palette on its static connecting text.
PALETTE_URL = "ui/palette.html"


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


class PaletteController(object):
    def __init__(self):
        self.palette = None
        fusion = FusionEnvironment()
        project_service = ProjectService(fusion, SettingsStore())
        identity_service = IdentityService(fusion)
        state_service = SceneStateService(fusion)
        scene_service = SceneService(fusion, SettingsStore())
        render_service = RenderService(fusion, SettingsStore())
        handlers = project_service.handlers()
        handlers.update(identity_service.handlers())
        handlers.update(state_service.handlers())
        handlers.update(scene_service.handlers())
        handlers.update(render_service.handlers())
        self.dispatcher = MessageDispatcher(handlers)
        # Fusion only holds weak references to event handlers; anything not
        # retained here is garbage collected and its events silently stop.
        self._handlers = []
        self._saw_palette_message = False

    def record_palette_message(self):
        """Leave a one-time Text Commands breadcrumb when the handshake works."""
        if not self._saw_palette_message:
            self._saw_palette_message = True
            _log("first palette message received; the page-to-add-in link works.")

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
            PALETTE_ID, PALETTE_NAME, PALETTE_URL, False, True, True, 460, 760
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
