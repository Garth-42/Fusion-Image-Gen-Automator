"""The only module in the initial skeleton that imports Fusion's adsk package."""
from __future__ import absolute_import

import json
import os

import adsk.core

from fmsm.messaging.dispatcher import MessageDispatcher

PALETTE_ID = "fmsm_scene_manager_palette"
PALETTE_NAME = "Fusion Manual Scene Manager"


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
        ui = app.userInterface
        self.palette = ui.palettes.itemById(PALETTE_ID)
        if self.palette is None:
            url = "file:///" + os.path.join(self._addin_root, "ui", "palette.html").replace("\\", "/")
            self.palette = ui.palettes.add(PALETTE_ID, PALETTE_NAME, url, True, True, True, 460, 760)
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
