import importlib
import sys
import types
from pathlib import Path

ADDIN_ROOT = Path(__file__).resolve().parents[2] / "addin" / "FusionManualSceneManager"
if str(ADDIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDIN_ROOT))


def _adapter_module(monkeypatch):
    adsk = types.ModuleType("adsk")
    core = types.ModuleType("adsk.core")
    adsk.core = core
    monkeypatch.setitem(sys.modules, "adsk", adsk)
    monkeypatch.setitem(sys.modules, "adsk.core", core)
    sys.modules.pop("fmsm.fusion.adapter", None)
    return importlib.import_module("fmsm.fusion.adapter")


def fake_environment(adapter_module, records):
    class FakeEnvironment(adapter_module.FusionEnvironment):
        def identity_records(self):
            return list(records)
    return FakeEnvironment()


def record(occurrence_id, occurrence_handle, component_id, component_key, label="Ball"):
    return {
        "occurrence_id": occurrence_id,
        "occurrence_handle": occurrence_handle,
        "component_id": component_id,
        "component_key": component_key,
        "label": label,
        "component_label": label,
    }


def scene(component_id):
    return {
        "assembly_state": {
            "occurrences": [
                {"occurrence_id": "11111111-1111-4111-8111-111111111111", "label": "Ball:1"},
                {"occurrence_id": "22222222-2222-4222-8222-222222222222", "label": "Ball:2"},
            ],
            "components": [{"component_id": component_id, "label": "Ball"}],
        }
    }


def test_repeated_occurrences_of_one_component_are_not_duplicate_component_ids(monkeypatch):
    adapter = _adapter_module(monkeypatch)
    component_id = "33333333-3333-4333-8333-333333333333"
    environment = fake_environment(adapter, [
        record("11111111-1111-4111-8111-111111111111", "occ-1", component_id, "component-token"),
        record("22222222-2222-4222-8222-222222222222", "occ-2", component_id, "component-token"),
    ])

    assert environment.validate_scene_references(scene(component_id)) == []


def test_distinct_components_with_same_component_id_remain_duplicate(monkeypatch):
    adapter = _adapter_module(monkeypatch)
    component_id = "33333333-3333-4333-8333-333333333333"
    environment = fake_environment(adapter, [
        record("11111111-1111-4111-8111-111111111111", "occ-1", component_id, "component-token-a"),
        record("22222222-2222-4222-8222-222222222222", "occ-2", component_id, "component-token-b"),
    ])

    assert environment.validate_scene_references(scene(component_id)) == [{
        "code": "DUPLICATE_COMPONENT_ID",
        "message": "More than one current component matches Ball.",
        "id": component_id,
        "label": "Ball",
    }]
