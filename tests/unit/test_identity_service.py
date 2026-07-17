import sys
import uuid
from pathlib import Path

ADDIN_ROOT = Path(__file__).resolve().parents[2] / "addin" / "FusionManualSceneManager"
if str(ADDIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDIN_ROOT))

from fmsm.application.identity_service import IdentityService


OCCURRENCE_A = "11111111-1111-4111-8111-111111111111"
COMPONENT_A = "33333333-3333-4333-8333-333333333333"


class FakeFusion(object):
    def __init__(self, records, document=True):
        self.records = records
        self.document = document

    def active_document(self):
        return {"name": "Fixture", "data_file_id": "fixture"} if self.document else None

    def identity_records(self):
        return [dict(record) for record in self.records]

    def write_occurrence_id(self, handle, value):
        self._record("occurrence_handle", handle)["occurrence_id"] = value

    def write_component_id(self, handle, value):
        self._record("component_handle", handle)["component_id"] = value

    def _record(self, field, handle):
        for record in self.records:
            if record[field] == handle:
                return record
        raise AssertionError("unknown handle")


def record(occurrence_handle, component_handle, occurrence_id=None, component_id=None, label="Part"):
    return {
        "occurrence_handle": occurrence_handle,
        "component_handle": component_handle,
        "component_key": component_handle,
        "occurrence_id": occurrence_id,
        "component_id": component_id,
        "label": label,
        "component_label": "Component " + component_handle,
    }


def test_status_reports_missing_and_duplicate_ids_without_host_handles():
    fusion = FakeFusion([
        record("occ-1", "component-1", OCCURRENCE_A, COMPONENT_A, "Rail:1"),
        record("occ-2", "component-2", OCCURRENCE_A, COMPONENT_A, "Rail:2"),
        record("occ-3", "component-3", None, None, "Cover:1"),
    ])

    result = IdentityService(fusion).status({})

    assert result["blocking_codes"] == ["DUPLICATE_OCCURRENCE_ID", "DUPLICATE_COMPONENT_ID"]
    assert result["duplicates"]["occurrences"] == [{"id": OCCURRENCE_A, "labels": ["Rail:1", "Rail:2"]}]
    assert result["missing"]["components"] == [{"label": "Component component-3"}]
    assert "occurrence_handle" not in str(result)


def test_ensure_ids_assigns_only_missing_or_invalid_ids_once_per_component():
    fusion = FakeFusion([
        record("occ-1", "component-1", OCCURRENCE_A, COMPONENT_A),
        record("occ-2", "component-1", None, COMPONENT_A),
        record("occ-3", "component-2", "not-a-uuid", None),
    ])

    result = IdentityService(fusion).ensure_ids({})

    assert result["assigned"] == {"occurrences": 2, "components": 1}
    assert all(uuid.UUID(item["occurrence_id"]) for item in fusion.records)
    assert all(uuid.UUID(item["component_id"]) for item in fusion.records)
    assert result["missing"] == {"occurrences": [], "components": []}


def test_repair_duplicates_preserves_first_entity_and_assigns_new_ids_to_others():
    fusion = FakeFusion([
        record("occ-1", "component-1", OCCURRENCE_A, COMPONENT_A),
        record("occ-2", "component-2", OCCURRENCE_A, COMPONENT_A),
    ])

    result = IdentityService(fusion).repair_duplicates({})

    assert result["repaired"] == {"occurrences": 1, "components": 1}
    assert fusion.records[0]["occurrence_id"] == OCCURRENCE_A
    assert fusion.records[0]["component_id"] == COMPONENT_A
    assert fusion.records[1]["occurrence_id"] != OCCURRENCE_A
    assert fusion.records[1]["component_id"] != COMPONENT_A
    assert result["blocking_codes"] == []
