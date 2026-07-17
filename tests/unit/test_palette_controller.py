import importlib
import json
import sys
import types


class _Event(object):
    def __init__(self):
        self.handlers = []

    def add(self, handler):
        self.handlers.append(handler)


class _Palette(object):
    def __init__(self):
        self.incomingFromHTML = _Event()
        self.closed = _Event()
        self.sent = []
        self.isVisible = False

    def sendInfoToHTML(self, action, data):
        self.sent.append((action, data))

    def deleteMe(self):
        pass


def _load_controller(monkeypatch, palette):
    adsk_module = types.ModuleType("adsk")
    core_module = types.ModuleType("adsk.core")
    core_module.HTMLEventHandler = object
    core_module.UserInterfaceGeneralEventHandler = object
    adsk_module.core = core_module
    monkeypatch.setitem(sys.modules, "adsk", adsk_module)
    monkeypatch.setitem(sys.modules, "adsk.core", core_module)
    sys.modules.pop("fmsm.fusion.palette_controller", None)
    controller_module = importlib.import_module("fmsm.fusion.palette_controller")

    class Palettes(object):
        def itemById(self, palette_id):
            return None

        def add(self, *arguments):
            self.arguments = arguments
            return palette

    palettes = Palettes()
    ui = type("Ui", (), {"palettes": palettes})()
    application = type("Application", (), {"userInterface": ui})()
    core_module.Application = type("ApplicationGetter", (), {"get": staticmethod(lambda: application)})
    return controller_module, palettes


def test_palette_uses_supported_browser_and_answers_ping(monkeypatch):
    palette = _Palette()
    controller_module, palettes = _load_controller(monkeypatch, palette)
    controller = controller_module.PaletteController("/add-in-root")

    controller.start()

    assert palettes.arguments[-1] is True
    request = json.dumps({
        "protocol_version": 1,
        "request_id": "00000000-0000-4000-8000-000000000001",
        "action": "system.ping",
        "payload": {},
    })
    args = type("Args", (), {"data": request})()
    palette.incomingFromHTML.handlers[0].notify(args)

    assert palette.sent[0][0] == "fmsm.response"
    assert json.loads(palette.sent[0][1])["result"] == {"message": "pong"}
