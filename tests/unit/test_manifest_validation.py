import copy
from pathlib import Path

from fmsm.domain.models import new_manifest
from fmsm.domain.validation import validate_manifest
from fmsm.infrastructure import yaml_store

EXAMPLE_MANIFEST = Path(__file__).resolve().parents[2] / "examples" / "manual.yaml"


def _valid_manifest():
    manifest = new_manifest(
        "0fbb1ed7-2e82-4e61-a5f8-83a2ed41e9db",
        "Printer E-Box Assembly Guide",
        "Printer E-Box Documentation Assembly",
        "urn:adsk.wipprod:dm.lineage:example-document",
    )
    manifest["project"]["scenes"] = [
        {"scene_id": "78b36cd7-532e-4d82-b8d7-b04ccbfa73ae", "file": "scenes/install-left-din-rail__78b36cd7.yaml"},
    ]
    return manifest


def _issue_codes(manifest):
    return [issue.code for issue in validate_manifest(manifest)]


def test_example_manifest_is_valid():
    assert validate_manifest(yaml_store.load(EXAMPLE_MANIFEST)) == []


def test_new_manifest_builder_output_is_valid():
    assert validate_manifest(_valid_manifest()) == []


def test_schema_version_is_required_and_pinned():
    manifest = _valid_manifest()
    del manifest["schema_version"]
    assert _issue_codes(manifest) == ["SCHEMA_VERSION_MISSING"]
    manifest["schema_version"] = 2
    assert _issue_codes(manifest) == ["SCHEMA_VERSION_UNSUPPORTED"]


def test_structural_faults_are_reported_with_paths():
    manifest = _valid_manifest()
    manifest["project"]["id"] = "not-a-uuid"
    manifest["project"]["title"] = ""
    manifest["project"]["source_document"]["role"] = "assembly"
    manifest["project"]["render_defaults"]["width_px"] = 1
    manifest["project"]["render_defaults"]["anti_alias"] = "yes"

    issues = validate_manifest(manifest)
    paths = {issue.path for issue in issues}
    assert all(issue.code == "MANIFEST_INVALID" for issue in issues)
    assert {"project.id", "project.title", "project.source_document.role",
            "project.render_defaults.width_px", "project.render_defaults.anti_alias"} <= paths


def test_scene_entries_reject_duplicates_and_unsafe_paths():
    manifest = _valid_manifest()
    entry = copy.deepcopy(manifest["project"]["scenes"][0])
    manifest["project"]["scenes"].append(entry)
    manifest["project"]["scenes"].append({"scene_id": "9a3dd5f1-532e-4d82-b8d7-b04ccbfa73ae", "file": "scenes/../escape.yaml"})

    issues = validate_manifest(manifest)
    assert [issue.path for issue in issues] == ["project.scenes.1.scene_id", "project.scenes.2.file"]
