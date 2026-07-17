"""Use cases for explicitly establishing stable Fusion entity identities."""
from __future__ import absolute_import

import uuid

from fmsm.application.errors import ServiceError
from fmsm.domain.identifiers import identity_report, valid_uuid


class IdentityService(object):
    """Coordinate identity operations through an injected Fusion port."""

    def __init__(self, fusion):
        self._fusion = fusion

    def handlers(self):
        return {
            "identity.status": self.status,
            "identity.ensure_ids": self.ensure_ids,
            "identity.repair_duplicates": self.repair_duplicates,
        }

    def status(self, payload):
        return self._summary(self._records())

    def ensure_ids(self, payload):
        records = self._records()
        assigned_occurrences = 0
        assigned_components = 0
        seen_components = set()
        for record in records:
            if not valid_uuid(record.get("occurrence_id")):
                self._write_occurrence_id(record["occurrence_handle"], str(uuid.uuid4()))
                assigned_occurrences += 1
            component_key = record["component_key"]
            if component_key in seen_components:
                continue
            seen_components.add(component_key)
            component_handle = record["component_handle"]
            if not valid_uuid(record.get("component_id")):
                self._write_component_id(component_handle, str(uuid.uuid4()))
                assigned_components += 1
        summary = self._summary(self._records())
        summary["assigned"] = {"occurrences": assigned_occurrences, "components": assigned_components}
        return summary

    def repair_duplicates(self, payload):
        records = self._records()
        repaired_occurrences = self._repair_occurrences(records)
        repaired_components = self._repair_components(records)
        summary = self._summary(self._records())
        summary["repaired"] = {"occurrences": repaired_occurrences, "components": repaired_components}
        return summary

    def _records(self):
        if self._fusion.active_document() is None:
            raise ServiceError("NO_ACTIVE_FUSION_DESIGN", "Open the documentation assembly before managing stable IDs.")
        return self._fusion.identity_records()

    def _repair_occurrences(self, records):
        by_id = {}
        for record in records:
            identifier = record.get("occurrence_id")
            if valid_uuid(identifier):
                by_id.setdefault(identifier, []).append(record)
        count = 0
        for identifier in sorted(by_id):
            for record in by_id[identifier][1:]:
                self._write_occurrence_id(record["occurrence_handle"], str(uuid.uuid4()))
                count += 1
        return count

    def _repair_components(self, records):
        by_id = {}
        seen_handles = set()
        for record in records:
            key = record["component_key"]
            if key in seen_handles:
                continue
            seen_handles.add(key)
            identifier = record.get("component_id")
            if valid_uuid(identifier):
                by_id.setdefault(identifier, []).append(record)
        count = 0
        for identifier in sorted(by_id):
            for record in by_id[identifier][1:]:
                self._write_component_id(record["component_handle"], str(uuid.uuid4()))
                count += 1
        return count

    def _write_occurrence_id(self, handle, identifier):
        try:
            self._fusion.write_occurrence_id(handle, identifier)
        except Exception:
            raise ServiceError("IDENTITY_ASSIGN_FAILED", "Fusion could not persist an occurrence UUID.")

    def _write_component_id(self, handle, identifier):
        try:
            self._fusion.write_component_id(handle, identifier)
        except Exception:
            raise ServiceError("IDENTITY_ASSIGN_FAILED", "Fusion could not persist a component UUID.")

    @staticmethod
    def _summary(records):
        report = identity_report(_primary_component_records(records))
        blocking = []
        if report["duplicate_occurrences"]:
            blocking.append("DUPLICATE_OCCURRENCE_ID")
        if report["duplicate_components"]:
            blocking.append("DUPLICATE_COMPONENT_ID")
        return {
            "occurrences": len(records),
            "components": len(_primary_component_records(records)),
            "missing": {
                "occurrences": report["missing_occurrences"],
                "components": report["missing_components"],
            },
            "duplicates": {
                "occurrences": report["duplicate_occurrences"],
                "components": report["duplicate_components"],
            },
            "blocking_codes": blocking,
        }


def _primary_component_records(records):
    primary = []
    seen_handles = set()
    for record in records:
        key = record["component_key"]
        if key in seen_handles:
            continue
        seen_handles.add(key)
        copy = dict(record)
        copy["component_is_primary"] = True
        primary.append(copy)
    return primary
