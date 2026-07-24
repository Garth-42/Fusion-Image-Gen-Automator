import importlib
import sys
import types
from pathlib import Path

import pytest

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


def test_missing_component_reference_does_not_block_scene_validation(monkeypatch):
    adapter = _adapter_module(monkeypatch)
    environment = fake_environment(adapter, [
        record("11111111-1111-4111-8111-111111111111", "occ-1", "44444444-4444-4444-8444-444444444444", "component-token"),
        record("22222222-2222-4222-8222-222222222222", "occ-2", "44444444-4444-4444-8444-444444444444", "component-token"),
    ])

    assert environment.validate_scene_references(scene("33333333-3333-4333-8333-333333333333")) == []


_IDENTITY_MATRIX = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def test_apply_scene_state_warns_on_missing_component_reference(monkeypatch):
    adapter = _adapter_module(monkeypatch)
    adapter.adsk.core.Matrix3D = _MatrixFactory
    environment = fake_environment(adapter, [
        record("11111111-1111-4111-8111-111111111111", _Occurrence(), "44444444-4444-4444-8444-444444444444", "component-token"),
        record("22222222-2222-4222-8222-222222222222", _Occurrence(), "44444444-4444-4444-8444-444444444444", "component-token"),
    ])
    environment._apply_camera = lambda camera: None
    environment._root_component = lambda: _RootComponent()
    scene_state = scene("33333333-3333-4333-8333-333333333333")  # component id absent from records
    scene_state["camera"] = {}
    for occurrence in scene_state["assembly_state"]["occurrences"]:
        occurrence["visible"] = True
        occurrence["transform_matrix_cm"] = list(_IDENTITY_MATRIX)

    result = environment.apply_scene_state(scene_state)

    assert result["warnings"] == [{"code": "COMPONENT_REFERENCE_MISSING", "label": "Ball"}]


def test_apply_scene_state_batches_transforms_and_sets_per_occurrence_opacity(monkeypatch):
    adapter = _adapter_module(monkeypatch)
    adapter.adsk.core.Matrix3D = _MatrixFactory
    occ_a, occ_b = _Occurrence(), _Occurrence()
    component_id = "44444444-4444-4444-8444-444444444444"
    environment = fake_environment(adapter, [
        record("11111111-1111-4111-8111-111111111111", occ_a, component_id, "token-a"),
        record("22222222-2222-4222-8222-222222222222", occ_b, component_id, "token-b"),
    ])
    environment._apply_camera = lambda camera: None
    root = _RootComponent()
    environment._root_component = lambda: root
    scene_state = scene(component_id)
    scene_state["camera"] = {}
    scene_state["assembly_state"]["occurrences"][0].update({"visible": True, "opacity": 0.4, "transform_matrix_cm": list(_IDENTITY_MATRIX)})
    scene_state["assembly_state"]["occurrences"][1].update({"visible": True, "opacity": 0.9, "transform_matrix_cm": list(_IDENTITY_MATRIX)})

    result = environment.apply_scene_state(scene_state)

    # Transforms replay in one root-context batch; the corrupting per-occurrence
    # transform2 assignment is gone, so the handles' transform2 is never touched.
    assert occ_a.transform2 is None and occ_b.transform2 is None
    assert len(root.transform_calls) == 1
    batched_occurrences, batched_transforms, ignore_joints = root.transform_calls[0]
    assert batched_occurrences == [occ_a, occ_b]
    assert len(batched_transforms) == 2 and ignore_joints is True
    # Opacity lands on each occurrence's assembly-context proxy, not the native.
    assert occ_a.component.createForAssemblyContext(occ_a).opacity == 0.4
    assert occ_b.component.createForAssemblyContext(occ_b).opacity == 0.9
    assert result["warnings"] == []


def test_apply_scene_state_falls_back_to_legacy_component_opacity(monkeypatch):
    adapter = _adapter_module(monkeypatch)
    adapter.adsk.core.Matrix3D = _MatrixFactory
    occ = _Occurrence()
    component_id = "44444444-4444-4444-8444-444444444444"
    environment = fake_environment(adapter, [
        record("11111111-1111-4111-8111-111111111111", occ, component_id, "token-a"),
    ])
    environment._apply_camera = lambda camera: None
    environment._root_component = lambda: _RootComponent()
    # A pre-migration scene: opacity only on the component, none on the occurrence.
    scene_state = {
        "camera": {},
        "assembly_state": {
            "occurrences": [{"occurrence_id": "11111111-1111-4111-8111-111111111111", "label": "Ball:1", "visible": True, "transform_matrix_cm": list(_IDENTITY_MATRIX)}],
            "components": [{"component_id": component_id, "label": "Ball", "opacity": 0.3}],
        },
    }

    environment.apply_scene_state(scene_state)

    assert occ.component.createForAssemblyContext(occ).opacity == 0.3


def test_export_viewport_png_rejects_a_reported_save_that_wrote_no_file(monkeypatch, tmp_path):
    adapter = _adapter_module(monkeypatch)

    class FakeViewport(object):
        def saveAsImageFile(self, path, width, height):
            return True  # reports success but writes nothing, as a read-only folder does

    class FakeApp(object):
        activeViewport = FakeViewport()

    adapter.adsk.core.Application = type("Application", (), {"get": staticmethod(lambda: FakeApp())})
    environment = adapter.FusionEnvironment()
    target = tmp_path / "generated" / "final.png"

    with pytest.raises(RuntimeError, match="none was written"):
        environment.export_viewport_png(str(target), 2400, 1600, True, True)


class _OpacityProxy(object):
    def __init__(self):
        self.opacity = 1.0


class _NativeComponent(object):
    """Hands back a stable per-occurrence proxy, like Component in Fusion."""

    def __init__(self):
        self._proxies = {}

    def createForAssemblyContext(self, occurrence):
        return self._proxies.setdefault(id(occurrence), _OpacityProxy())


class _Occurrence(object):
    def __init__(self):
        self.isLightBulbOn = False
        self.transform2 = None
        self.component = _NativeComponent()


class _RootComponent(object):
    def __init__(self):
        self.transform_calls = []

    def transformOccurrences(self, occurrences, transforms, ignore_joints):
        self.transform_calls.append((list(occurrences), list(transforms), ignore_joints))
        return True


class _MatrixFactory(object):
    @staticmethod
    def create():
        return _Matrix()


class _Matrix(object):
    def __init__(self):
        self.values = None

    def setWithArray(self, values):
        self.values = list(values)
