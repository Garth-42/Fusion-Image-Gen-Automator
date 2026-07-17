"""Fusion palette adapter; this is the only initial module that imports ``adsk``."""
from __future__ import absolute_import

import json
import os

import adsk.core

from fmsm.messaging.dispatcher import MessageDispatcher

PALETTE_ID = "fmsm_scene_manager_palette"
PALETTE_NAME = "Fusion Manual Scene Manager"


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
        response = self._controller.dispatcher.dispatch(args.data)
        self._controller.palette.sendInfoToHTML("fmsm.response", json.dumps(response))


class _ClosedHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def __init__(self, controller):
        super(_ClosedHandler, self).__init__()
        self._controller = controller

    def notify(self, args):
        self._controller.palette = None


class PaletteController(object):
    def __init__(self, addin_root):
        self._addin_root = addin_root
        self.palette = None
        self.dispatcher = MessageDispatcher()
        self._handlers = []

    def start(self):
        app = adsk.core.Application.get()
        if app is None:
            raise RuntimeError("Fusion application is unavailable.")
        ui = app.userInterface
        if ui is None:
            raise RuntimeError("Fusion user interface is unavailable.")
        self.palette = ui.palettes.itemById(PALETTE_ID)
        if self.palette is None:
            url = "file:///" + os.path.join(self._addin_root, "ui", "palette.html").replace("\\", "/")
            # Keep the document hidden until the event handlers below are
            # installed.  Creating it visible lets its script send the one-time
            # initial request before ``incomingFromHTML`` has a subscriber.
            self.palette = ui.palettes.add(
                PALETTE_ID, PALETTE_NAME, url, False, True, True, 460, 760
            )
        if self.palette is None:
            raise RuntimeError("Fusion did not create the FMSM palette.")
        incoming = _IncomingHtmlHandler(self)
        closed = _ClosedHandler(self)
        self.palette.incomingFromHTML.add(incoming)
        self.palette.closed.add(closed)
        self._handlers.extend([incoming, closed])
        self.palette.isVisible = True

    def stop(self):
        if self.palette is not None:
            self.palette.deleteMe()
        self.palette = None
        self._handlers = []
