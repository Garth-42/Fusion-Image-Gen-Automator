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

    def __init__(self, document=DOCUMENT, confirm=True, folder=None, project_id=None, file=None):
        self.document = dict(document) if document is not None else None
        self.confirm_answer = confirm
        self.folder = folder
        # The file the user picks in the open dialog. Defaults to the manifest
        # inside ``folder`` so a test can describe a project by its folder.
        self.file = file
        self.project_id = project_id
        self.confirmations = []
        self.folder_prompts = []
        self.file_prompts = []

    def active_document(self):
        return dict(self.document) if self.document is not None else None

    def confirm(self, message):
        self.confirmations.append(message)
        return self.confirm_answer

    def choose_folder(self, title, initial_directory=None):
        self.folder_prompts.append({"title": title, "initial_directory": initial_directory})
        return str(self.folder) if self.folder is not None else None

    def choose_file(self, title, file_filter, initial_directory=None, initial_filename=None):
        self.file_prompts.append({
            "title": title, "filter": file_filter,
            "initial_directory": initial_directory, "initial_filename": initial_filename,
        })
        if self.file is not None:
            return str(self.file)
        return str(self.folder / "manual.yaml") if self.folder is not None else None

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


def test_initialize_rejects_document_that_already_has_project_id(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    service, fusion, _ = _service(
        tmp_path, folder=root, project_id="0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"
    )

    with pytest.raises(ServiceError) as excinfo:
        service.initialize({"title": "Replacement"})

    assert excinfo.value.code == "PROJECT_ALREADY_ASSOCIATED"
    assert excinfo.value.details == {"project_id": "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"}
    assert fusion.confirmations == []
    assert fusion.folder_prompts == []
    assert not (root / "manual.yaml").exists()


def test_initialize_can_replace_existing_project_association_when_requested(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    old_project_id = "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"
    service, fusion, settings = _service(tmp_path, folder=root, project_id=old_project_id)

    result = service.initialize({"title": "Replacement", "replace_association": True})

    manifest = yaml_store.load(root / "manual.yaml")
    assert manifest["project"]["id"] != old_project_id
    assert fusion.project_id == manifest["project"]["id"]
    assert settings.project_root(fusion.project_id) == str(root)
    assert result["project"]["title"] == "Replacement"


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
    assert [(entry["scene_id"], entry["file"]) for entry in result["project"]["scenes"]] == [
        (scenes[0]["scene_id"], scenes[0]["file"])
    ]
    assert result["project"]["file"] == str(root / "manual.yaml")
    assert result["warnings"] == []


def test_open_prompts_for_the_project_file_not_a_folder(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, _ = _service(tmp_path, folder=root)

    service.open({})

    assert fusion.folder_prompts == []
    assert len(fusion.file_prompts) == 1
    assert "manual.yaml" in fusion.file_prompts[0]["title"]


def test_open_rejects_a_file_that_is_not_a_project_file(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    other = root / "notes.yaml"
    other.write_text("schema_version: 1\n", encoding="utf-8")
    service, fusion, settings = _service(tmp_path, file=other)

    with pytest.raises(ServiceError) as excinfo:
        service.open({})

    assert excinfo.value.code == "PROJECT_FILE_INVALID"
    assert fusion.project_id is None
    assert settings.document_project_file(DOCUMENT["data_file_id"]) is None


def test_open_reports_a_selected_file_that_does_not_exist(tmp_path):
    service, _, _ = _service(tmp_path, file=tmp_path / "gone" / "manual.yaml")
    with pytest.raises(ServiceError) as excinfo:
        service.open({})
    assert excinfo.value.code == "PROJECT_FILE_NOT_FOUND"


def test_open_stops_cleanly_when_the_file_dialog_is_cancelled(tmp_path):
    service, fusion, _ = _service(tmp_path)
    assert service.open({}) == {"cancelled": True}
    assert fusion.project_id is None


def test_open_remembers_the_project_file_for_each_cad_document(tmp_path):
    root_a = tmp_path / "manual-a"
    root_b = tmp_path / "elsewhere" / "manual-b"
    _existing_project(root_a)
    _existing_project(root_b)
    other_document = {"name": "Other Assembly", "data_file_id": "urn:adsk:lineage:doc-2"}
    service_a, fusion_a, settings = _service(tmp_path, folder=root_a)
    service_b = ProjectService(FakeFusion(document=other_document, folder=root_b), settings)

    service_a.open({})
    service_b.open({})

    # Each document keeps its own location; the later open does not displace it.
    assert settings.document_project_file(DOCUMENT["data_file_id"]) == str(root_a / "manual.yaml")
    assert settings.document_project_file(other_document["data_file_id"]) == str(root_b / "manual.yaml")
    # The next dialog for the first document starts in that document's folder,
    # with the project file name filled in.
    service_a.open({})
    assert fusion_a.file_prompts[-1]["initial_directory"] == str(root_a)
    assert fusion_a.file_prompts[-1]["initial_filename"] == "manual.yaml"


def test_open_dialog_falls_back_to_the_last_used_location_for_a_new_document(tmp_path):
    root = tmp_path / "manual-a"
    _existing_project(root)
    service, _, settings = _service(tmp_path, folder=root)
    service.open({})
    newcomer = FakeFusion(document={"name": "New Assembly", "data_file_id": "urn:adsk:lineage:doc-9"})

    ProjectService(newcomer, settings).open({})

    assert newcomer.file_prompts[0]["initial_directory"] == str(root)


def test_open_dialog_ignores_a_remembered_location_that_no_longer_exists(tmp_path):
    root = tmp_path / "manual-a"
    _existing_project(root)
    service, fusion, settings = _service(tmp_path, folder=root)
    settings.record_project(
        "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db", tmp_path / "deleted",
        DOCUMENT["data_file_id"], str(tmp_path / "deleted" / "manual.yaml"),
    )

    service.open({})

    assert fusion.file_prompts[0]["initial_directory"] is None


def test_status_offers_the_remembered_project_file_when_the_link_was_not_saved(tmp_path):
    # The add-in never saves the Fusion document, so a link written during one
    # session is gone the next time unless the user saved. The project is still
    # where it was; status must say so instead of presenting a blank slate.
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, _ = _service(tmp_path, folder=root)
    service.open({})
    fusion.project_id = None

    result = service.status({})

    assert result["project"] is None
    assert result["remembered_project_file"] == str(root / "manual.yaml")


def test_status_does_not_offer_a_remembered_file_that_is_gone(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, _ = _service(tmp_path, folder=root)
    service.open({})
    fusion.project_id = None
    (root / "manual.yaml").unlink()

    assert "remembered_project_file" not in service.status({})


def test_open_can_reuse_the_remembered_file_without_a_dialog(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, _ = _service(tmp_path, folder=root)
    service.open({})
    fusion.project_id = None
    fusion.file_prompts = []

    result = service.open({"use_remembered": True})

    assert fusion.file_prompts == []
    assert fusion.project_id == "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"
    assert result["project"]["root"] == str(root)


def test_open_remembered_fails_clearly_when_nothing_is_remembered(tmp_path):
    service, fusion, _ = _service(tmp_path)
    with pytest.raises(ServiceError) as excinfo:
        service.open({"use_remembered": True})
    assert excinfo.value.code == "PROJECT_FILE_NOT_FOUND"
    assert fusion.file_prompts == []


def test_unsaved_documents_are_not_remembered_individually(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    unsaved = {"name": "Untitled", "data_file_id": None}
    service, fusion, settings = _service(tmp_path, document=unsaved, folder=root)

    service.open({})
    fusion.project_id = None

    # No stable identity to key on, so nothing is offered for "this" document,
    # but the location still seeds the next dialog.
    assert "remembered_project_file" not in service.status({})
    assert settings.last_project_file() == str(root / "manual.yaml")


def test_open_asks_before_relinking_a_document_to_a_different_project(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, settings = _service(
        tmp_path, folder=root, project_id="99999999-9999-4999-8999-999999999999", confirm=False
    )

    assert service.open({}) == {"cancelled": True}

    assert len(fusion.confirmations) == 1
    assert fusion.project_id == "99999999-9999-4999-8999-999999999999"
    assert settings.document_project_file(DOCUMENT["data_file_id"]) is None


def test_open_relinks_a_document_once_the_user_confirms(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, _ = _service(
        tmp_path, folder=root, project_id="99999999-9999-4999-8999-999999999999", confirm=True
    )

    result = service.open({})

    assert fusion.project_id == "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"
    assert result["project"]["root"] == str(root)


def test_reopening_the_linked_project_asks_nothing(tmp_path):
    root = tmp_path / "repo"
    _existing_project(root)
    service, fusion, _ = _service(tmp_path, folder=root, project_id="0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db")

    service.open({})

    assert fusion.confirmations == []


def test_initialize_remembers_the_new_project_for_the_document(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    service, _, settings = _service(tmp_path, folder=root)

    service.initialize({"title": "Guide"})

    assert settings.document_project_file(DOCUMENT["data_file_id"]) == str(root / "manual.yaml")


def test_status_lists_a_scene_whose_file_is_unreadable_instead_of_failing(tmp_path):
    # One hand-edited scene file used to turn every status request into an
    # INTERNAL_ERROR, leaving the palette with no project at all.
    root = tmp_path / "repo"
    project_id = "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db"
    scenes = [
        {"scene_id": "78b36cd7-532e-4d82-b8d7-b04ccbfa73ae", "file": "scenes/broken__78b36cd7.yaml"},
        {"scene_id": "88b36cd7-532e-4d82-b8d7-b04ccbfa73ae", "file": "scenes/missing__88b36cd7.yaml"},
    ]
    _existing_project(root, scenes)
    (root / "scenes").mkdir()
    (root / "scenes" / "broken__78b36cd7.yaml").write_text("scene: [unterminated\n", encoding="utf-8")
    service, _, settings = _service(tmp_path, project_id=project_id)
    settings.record_project(project_id, root)

    result = service.status({})

    listed = result["project"]["scenes"]
    assert [entry["scene_id"] for entry in listed] == [scenes[0]["scene_id"], scenes[1]["scene_id"]]
    assert "cannot be read" in listed[0]["error"]
    assert "missing" in listed[1]["error"]


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
