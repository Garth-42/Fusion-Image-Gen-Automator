import importlib
import sys
import types


def _load_bootstrap(monkeypatch):
    adsk_module = types.ModuleType("adsk")
    core_module = types.ModuleType("adsk.core")
    core_module.HTMLEventHandler = object
    core_module.UserInterfaceGeneralEventHandler = object
    core_module.Application = type("Application", (), {"get": staticmethod(lambda: None)})
    adsk_module.core = core_module
    monkeypatch.setitem(sys.modules, "adsk", adsk_module)
    monkeypatch.setitem(sys.modules, "adsk.core", core_module)
    sys.modules.pop("fmsm.fusion.palette_controller", None)
    sys.modules.pop("bootstrap", None)
    return importlib.import_module("bootstrap")


def test_run_reports_startup_failure(monkeypatch):
    bootstrap = _load_bootstrap(monkeypatch)
    captured = []

    class FailingController(object):
        def __init__(self, root):
            pass

        def start(self):
            raise RuntimeError("palette unavailable")

    monkeypatch.setattr(bootstrap, "PaletteController", FailingController)
    monkeypatch.setattr(bootstrap, "report_startup_failure", captured.append)

    bootstrap.run(None)

    assert bootstrap._controller is None
    assert "palette unavailable" in captured[0]
