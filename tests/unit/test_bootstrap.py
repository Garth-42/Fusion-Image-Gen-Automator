import importlib
import sys
import types


def _load_bootstrap(monkeypatch):
    adsk_module = types.ModuleType("adsk")
    core_module = types.ModuleType("adsk.core")
    core_module.HTMLEventHandler = object
    core_module.Application = type("Application", (), {"get": staticmethod(lambda: None)})
    adsk_module.core = core_module
    monkeypatch.setitem(sys.modules, "adsk", adsk_module)
    monkeypatch.setitem(sys.modules, "adsk.core", core_module)
    sys.modules.pop("fmsm.fusion.palette_controller", None)
    sys.modules.pop("bootstrap", None)
    return importlib.import_module("bootstrap")


def test_run_reports_startup_failure_and_cleans_up(monkeypatch):
    bootstrap = _load_bootstrap(monkeypatch)
    captured = []
    stopped = []

    class FailingController(object):
        def start(self):
            raise RuntimeError("palette unavailable")

        def stop(self):
            stopped.append(True)

    monkeypatch.setattr(bootstrap, "PaletteController", FailingController)
    monkeypatch.setattr(bootstrap, "report_startup_failure", captured.append)

    bootstrap.run(None)

    # A failed start must not leak a half-built palette: the next run would
    # find it via itemById and adopt a page that can no longer respond.
    assert stopped == [True]
    assert bootstrap._controller is None
    assert "palette unavailable" in captured[0]
