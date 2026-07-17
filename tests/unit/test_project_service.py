import pytest

from fmsm.application.errors import ServiceError
from fmsm.application.services import ProjectService
from fmsm.domain.models import new_manifest
from fmsm.domain.validation import validate_manifest
from fmsm.infrastructure import yaml_store
from fmsm.infrastructure.settings_store import SettingsStore

DOCUMENT = {"name": "E-Box Documentation Assembly", "data_file_id": "urn:adsk:lineage:doc-1"}


class FakeFusion(object):
    """Scripted stand-in for the Fusion environment port."""

    def __init__(self, document=DOCUMENT, confirm=True, folder=None, project_id=None):
        self.document = dict(document) if document is not None else None
        self.confirm_answer = confirm
        self.folder = folder
        self.project_id = project_id
        self.confirmations = []
        self.folder_prompts = []

    def active_document(self):
        return dict(self.document) if self.document is not None else None

    def confirm(self, message):
        self.confirmations.append(message)
        return self.confirm_answer

    def choose_folder(self, title):
        self.folder_prompts.append(title)
        return str(self.folder) if self.folder is not None else None

    def read_project_id(self):
        return self.project_id

    def write_project_id(self, project_id):
        self.project_id = project_id


def _service(tmp_path, **fusion_kwargs):
    fusion = FakeFusion(**fusion_kwargs)
    settings = SettingsStore(tmp_path / "settings.json")
    return ProjectService(fusion, settings), fusion, settings


def _existing_project(root, scenes=()):
    manifest = new_manifest(
        "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db",
        "Printer E-Box Assembly Guide",
        DOCUMENT["name"],
        DOCUMENT["data_file_id"],
    )
    manifest["project"]["scenes"] = list(scenes)
    root.mkdir(parents=True, exist_ok=True)
    yaml_store.write(root, "manual.yaml", manifest)
    return manifest


def test_initialize_creates_a_valid_associated_project(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    service, fusion, settings = _service(tmp_path, folder=root)

    result = service.initialize({"title": "  Printer E-Box Assembly Guide  "})

    manifest = yaml_store.load(root / "manual.yaml")
    assert validate_manifest(manifest) == []
    assert manifest["project"]["title"] == "Printer E-Box Assembly Guide"
    assert manifest["project"]["source_document"]["data_file_id"] == DOCUMENT["data_file_id"]
    for relative in ("scenes", "assets/generated", "assets/thumbnails"):
        assert (root / relative).is_dir()
    project_id = manifest["project"]["id"]
    assert fusion.project_id == project_id
    assert settings.project_root(project_id) == str(root)
    assert result["project"]["title"] == "Printer E-Box Assembly Guide"
    assert result["project"]["scenes"] == []
    assert result["document"]["name"] == DOCUMENT["name"]
    assert result["warnings"] == []


def test_initialize_requires_a_usable_title(tmp_path):
    service, _, _ = _service(tmp_path)
    with pytest.raises(ServiceError) as excinfo:
        service.initialize({"title": "   "})
    assert excinfo.value.code == "PROJECT_TITLE_INVALID"


def test_initialize_requires_an_active_document(tmp_path):
    service, _, _ = _service(tmp_path, document=None)
    with pytest.raises(ServiceError) as excinfo:
        service.initialize({"title": "Guide"})
    assert excinfo.value.code == "NO_ACTIVE_FUSION_DESIGN"


def test_initialize_stops_cleanly_on_declined_confirmation(tmp_path):
    service, fusion, _ = _service(tmp_path, confirm=False)
    assert service.initialize({"title": "Guide"}) == {"cancelled": True}
    assert fusion.folder_prompts == []


def test_initialize_stops_cleanly_on_folder_cancel(tmp_path):
    service, _, _ = _service(tmp_path, folder=None)
    assert service.initialize({"title": "Guide"}) == {"cancelled": True}


def test_initialize_refuses_a_folder_with_an_existing_manifest(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, _, _ = _service(tmp_path, folder=root)
    with pytest.raises(ServiceError) as excinfo:
        service.initialize({"title": "Guide"})
    assert excinfo.value.code == "PROJECT_ROOT_NOT_EMPTY"


def test_initialize_warns_when_document_was_never_saved(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    unsaved = {"name": "Untitled", "data_file_id": None}
    service, _, _ = _service(tmp_path, document=unsaved, folder=root)

    result = service.initialize({"title": "Guide"})

    assert [warning["code"] for warning in result["warnings"]] == ["DOCUMENT_ID_WEAK"]
    manifest = yaml_store.load(root / "manual.yaml")
    assert manifest["project"]["source_document"]["data_file_id"] is None


def test_open_associates_document_and_lists_scenes(tmp_path):
    root = tmp_path / "repo"
    scenes = [{"scene_id": "78b36cd7-532e-4d82-b8d7-b04ccbfa73ae", "file": "scenes/install-left-din-rail__78b36cd7.yaml"}]
    _existing_project(root, scenes)
    service, fusion, settings = _service(tmp_path, folder=root)

    result = service.open({})

    assert fusion.project_id == "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"
    assert settings.project_root(fusion.project_id) == str(root)
    assert result["project"]["scenes"] == scenes
    assert result["warnings"] == []


def test_open_requires_a_manifest_in_the_selected_folder(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    service, _, _ = _service(tmp_path, folder=root)
    with pytest.raises(ServiceError) as excinfo:
        service.open({})
    assert excinfo.value.code == "PROJECT_ROOT_UNRESOLVED"


def test_open_rejects_a_project_conflicting_with_the_document(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, _ = _service(
        tmp_path, folder=root, project_id="99999999-9999-4999-8999-999999999999"
    )
    with pytest.raises(ServiceError) as excinfo:
        service.open({})
    assert excinfo.value.code == "PROJECT_ID_MISMATCH"
    assert fusion.project_id == "99999999-9999-4999-8999-999999999999"


def test_open_surfaces_manifest_faults_with_stable_codes(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "manual.yaml").write_text("schema_version: 2\nproject: {}\n", encoding="utf-8")
    service, _, _ = _service(tmp_path, folder=root)
    with pytest.raises(ServiceError) as excinfo:
        service.open({})
    assert excinfo.value.code == "SCHEMA_VERSION_UNSUPPORTED"


def test_open_warns_on_source_document_mismatch(tmp_path):
    root = tmp_path / "repo"
    manifest = _existing_project(root)
    other_document = {"name": "Other Assembly", "data_file_id": "urn:adsk:lineage:doc-2"}
    service, _, _ = _service(tmp_path, document=other_document, folder=root)

    result = service.open({})

    assert [warning["code"] for warning in result["warnings"]] == ["SOURCE_DOCUMENT_MISMATCH"]
    assert result["project"]["id"] == manifest["project"]["id"]


def test_status_reports_unassociated_document(tmp_path):
    service, _, _ = _service(tmp_path)
    assert service.status({}) == {"document": DOCUMENT, "project": None, "warnings": []}


def test_status_reports_no_document(tmp_path):
    service, _, _ = _service(tmp_path, document=None)
    assert service.status({}) == {"document": None, "project": None, "warnings": []}


def test_status_flags_an_unresolved_root_for_an_associated_document(tmp_path):
    service, _, _ = _service(tmp_path, project_id="0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db")

    result = service.status({})

    assert result["project"] is None
    assert [warning["code"] for warning in result["warnings"]] == ["PROJECT_ROOT_UNRESOLVED"]


def test_status_resolves_a_previously_opened_project(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, settings = _service(
        tmp_path, folder=root, project_id="0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"
    )
    settings.record_project("0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db", root)

    result = service.status({})

    assert result["project"]["title"] == "Printer E-Box Assembly Guide"
    assert result["project"]["root"] == str(root)
