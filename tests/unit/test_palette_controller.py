import importlib
import json
import sys
import types


class _Event(object):
    def __init__(self, lifecycle, name):
        self.handlers = []
        self._lifecycle = lifecycle
        self._name = name

    def add(self, handler):
        self.handlers.append(handler)
        self._lifecycle.append(self._name)


class _Palette(object):
    def __init__(self):
        self.lifecycle = []
        self.incomingFromHTML = _Event(self.lifecycle, "incoming")
        self.closed = _Event(self.lifecycle, "closed")
        self.sent = []
        self._is_visible = False

    @property
    def isVisible(self):
        return self._is_visible

    @isVisible.setter
    def isVisible(self, value):
        self._is_visible = value
        if value:
            self.lifecycle.append("visible")

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


def test_palette_subscribes_before_making_document_visible(monkeypatch):
    palette = _Palette()
    controller_module, palettes = _load_controller(monkeypatch, palette)
    controller = controller_module.PaletteController("/add-in-root")

    controller.start()

    assert palettes.arguments[3] is False
    assert palettes.arguments[2] == "file:///add-in-root/ui/palette.html"
    assert palette.incomingFromHTML.handlers
    assert palette.closed.handlers
    assert palette.isVisible is True
    assert palette.lifecycle == ["incoming", "closed", "visible"]
    request = json.dumps({
        "protocol_version": 1,
        "request_id": "00000000-0000-4000-8000-000000000001",
        "action": "system.ping",
        "payload": {},
    })
    args = type("Args", (), {"data": request, "returnData": None})()
    palette.incomingFromHTML.handlers[0].notify(args)

    # The response travels back through ``returnData`` (the return value of the
    # JavaScript ``fusionSendData`` call), not ``sendInfoToHTML``, so it is
    # delivered even while the old browser blocks the palette's JS thread.
    assert palette.sent == []
    assert json.loads(args.returnData)["result"] == {"message": "pong"}
