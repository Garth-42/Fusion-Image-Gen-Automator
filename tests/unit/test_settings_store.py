import json

from fmsm.infrastructure.settings_store import SettingsStore


def test_missing_settings_file_resolves_no_root(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    assert store.project_root("0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db") is None


def test_recorded_project_round_trips_and_preserves_others(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.record_project("11111111-1111-4111-8111-111111111111", "/work/manual-a")
    store.record_project("22222222-2222-4222-8222-222222222222", "/work/manual-b")

    assert store.project_root("11111111-1111-4111-8111-111111111111") == "/work/manual-a"
    assert store.project_root("22222222-2222-4222-8222-222222222222") == "/work/manual-b"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["projects"]["11111111-1111-4111-8111-111111111111"]["last_opened"].endswith("Z")


def test_corrupt_settings_file_self_heals(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    store = SettingsStore(path)

    assert store.project_root("11111111-1111-4111-8111-111111111111") is None
    store.record_project("11111111-1111-4111-8111-111111111111", "/work/manual-a")
    assert store.project_root("11111111-1111-4111-8111-111111111111") == "/work/manual-a"
