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
        self.sent = []
        self.deleted = False
        self._is_visible = False
        self.width = 460
        self.height = 760
        self.sizes = []

    def setSize(self, width, height):
        self.width = width
        self.height = height
        self.sizes.append((width, height))

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
        self.deleted = True


def _load_controller(monkeypatch, palette, existing_palette=None):
    adsk_module = types.ModuleType("adsk")
    core_module = types.ModuleType("adsk.core")
    core_module.HTMLEventHandler = object
    adsk_module.core = core_module
    monkeypatch.setitem(sys.modules, "adsk", adsk_module)
    monkeypatch.setitem(sys.modules, "adsk.core", core_module)
    sys.modules.pop("fmsm.fusion.palette_controller", None)
    controller_module = importlib.import_module("fmsm.fusion.palette_controller")

    class Palettes(object):
        def itemById(self, palette_id):
            return existing_palette

        def add(self, *arguments):
            self.arguments = arguments
            return palette

    palettes = Palettes()
    ui = type("Ui", (), {"palettes": palettes})()
    application = type("Application", (), {"userInterface": ui, "log": lambda self, text: None})()
    core_module.Application = type("ApplicationGetter", (), {"get": staticmethod(lambda: application)})
    return controller_module, palettes


def _ping_request():
    return json.dumps({
        "protocol_version": 1,
        "request_id": "00000000-0000-4000-8000-000000000001",
        "action": "system.ping",
        "payload": {},
    })


def test_palette_subscribes_before_making_document_visible(monkeypatch):
    palette = _Palette()
    controller_module, palettes = _load_controller(monkeypatch, palette)
    controller = controller_module.PaletteController()

    controller.start()

    # The URL must stay the documented Palettes.add form: a path relative to
    # the add-in root. Absolute file:// URIs have loaded the document while
    # quietly breaking everything around it.
    assert palettes.arguments[2] == "ui/palette.html"
    assert palettes.arguments[3] is False
    assert palette.incomingFromHTML.handlers
    assert palette.isVisible is True
    assert palette.lifecycle == ["incoming", "visible"]

    args = type("Args", (), {"data": _ping_request(), "returnData": None})()
    palette.incomingFromHTML.handlers[0].notify(args)

    # The response travels back through ``returnData`` (the return value of the
    # JavaScript ``fusionSendData`` call), not ``sendInfoToHTML``, so it is
    # delivered even while the old browser blocks the palette's JS thread.
    assert palette.sent == []
    assert json.loads(args.returnData)["result"] == {"message": "pong"}


def test_first_requests_resize_the_window_so_the_palette_cannot_stay_blank(monkeypatch):
    palette = _Palette()
    controller_module, _ = _load_controller(monkeypatch, palette)
    controller = controller_module.PaletteController()
    controller.start()

    handler = palette.incomingFromHTML.handlers[0]
    for _ in range(controller_module.STARTUP_REPAINT_NUDGES + 2):
        handler.notify(type("Args", (), {"data": _ping_request(), "returnData": None})())

    # The Qt WebEngine palette paints its first frame before layout settles and
    # then never repaints, leaving the window blank until the user collapses and
    # re-expands it. Nothing the page can do from inside the document fixes
    # that; only a resize of the window itself does, and only the add-in can
    # perform one. Each startup request must therefore grow the window a pixel
    # and put it straight back.
    assert palette.sizes[:2] == [(460, 761), (460, 760)]
    # Bounded to the startup burst: past that the user may have sized the
    # window themselves, and nothing should be moving it.
    assert len(palette.sizes) == 2 * controller_module.STARTUP_REPAINT_NUDGES
    assert (palette.width, palette.height) == (460, 760)


def test_the_repaint_resize_waits_until_the_request_is_answered(monkeypatch):
    palette = _Palette()
    controller_module, _ = _load_controller(monkeypatch, palette)
    controller = controller_module.PaletteController()
    controller.start()

    args = type("Args", (), {"data": _ping_request(), "returnData": None})()
    seen = []
    palette.setSize = lambda width, height: seen.append(args.returnData)

    palette.incomingFromHTML.handlers[0].notify(args)

    # Resizing the palette can pump the event loop, which could let the page
    # send its next request straight back into the dispatcher. Answering first
    # means there is never a half-finished request to re-enter.
    assert seen and all(response is not None for response in seen)


def test_a_palette_that_refuses_to_resize_does_not_fail_the_request(monkeypatch):
    palette = _Palette()
    controller_module, _ = _load_controller(monkeypatch, palette)
    controller = controller_module.PaletteController()
    controller.start()

    def refuse(width, height):
        raise RuntimeError("this palette is docked")

    palette.setSize = refuse
    args = type("Args", (), {"data": _ping_request(), "returnData": None})()

    palette.incomingFromHTML.handlers[0].notify(args)

    # Docked palettes own their geometry and can reject setSize. A cosmetic
    # repaint must never turn into a failed request.
    assert json.loads(args.returnData)["result"] == {"message": "pong"}


def test_start_replaces_a_palette_left_over_from_an_earlier_run(monkeypatch):
    stale = _Palette()
    fresh = _Palette()
    controller_module, palettes = _load_controller(monkeypatch, fresh, existing_palette=stale)
    controller = controller_module.PaletteController()

    controller.start()

    # A leftover palette still shows the page of the run that created it, whose
    # script gave up retrying long ago; it must be rebuilt, never reused.
    assert stale.deleted is True
    assert controller.palette is fresh
    assert fresh.incomingFromHTML.handlers


def test_stop_tolerates_a_palette_fusion_already_deleted(monkeypatch):
    palette = _Palette()
    controller_module, _ = _load_controller(monkeypatch, palette)
    controller = controller_module.PaletteController()
    controller.start()

    def explode():
        raise RuntimeError("palette is no longer valid")

    palette.deleteMe = explode

    controller.stop()

    assert controller.palette is None
