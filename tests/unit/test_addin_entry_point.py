import importlib
import sys
import types


def _load_entry_point(monkeypatch):
    adsk_module = types.ModuleType("adsk")
    core_module = types.ModuleType("adsk.core")
    core_module.Application = type("Application", (), {"get": staticmethod(lambda: None)})
    core_module.HTMLEventHandler = object
    adsk_module.core = core_module
    monkeypatch.setitem(sys.modules, "adsk", adsk_module)
    monkeypatch.setitem(sys.modules, "adsk.core", core_module)
    sys.modules.pop("FusionManualSceneManager", None)
    return importlib.import_module("FusionManualSceneManager")


def test_run_reports_a_bootstrap_import_failure(monkeypatch):
    entry_point = _load_entry_point(monkeypatch)
    failures = []

    def fail_to_load():
        raise ImportError("bootstrap module unavailable")

    monkeypatch.setattr(entry_point, "_load_bootstrap", fail_to_load)
    monkeypatch.setattr(entry_point, "_report_failure", lambda operation, detail: failures.append((operation, detail)))

    entry_point.run(None)

    assert failures[0][0] == "start"
    assert "bootstrap module unavailable" in failures[0][1]


def test_load_bootstrap_adds_its_own_directory(monkeypatch):
    entry_point = _load_entry_point(monkeypatch)
    monkeypatch.delitem(sys.modules, "bootstrap", raising=False)
    monkeypatch.setattr(entry_point.sys, "path", [])

    entry_point._load_bootstrap()

    assert entry_point.ADDIN_ROOT in entry_point.sys.path
