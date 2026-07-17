"""Fusion implementation of the application-layer environment port."""
from __future__ import absolute_import

import adsk.core

from fmsm.application.ports import FusionEnvironmentPort

ATTRIBUTE_GROUP = "FMSM"
PROJECT_ID_ATTRIBUTE = "project_id"
OCCURRENCE_ID_ATTRIBUTE = "occurrence_id"
COMPONENT_ID_ATTRIBUTE = "component_id"
DIALOG_TITLE = "Fusion Manual Scene Manager"


class FusionEnvironment(FusionEnvironmentPort):
    """Talks to the live Fusion session; runs only on Fusion event callbacks."""

    def _app(self):
        app = adsk.core.Application.get()
        if app is None:
            raise RuntimeError("Fusion application is unavailable.")
        return app

    def _document(self):
        document = self._app().activeDocument
        if document is None:
            raise RuntimeError("No active Fusion document.")
        return document

    def active_document(self):
        document = self._app().activeDocument
        if document is None:
            return None
        data_file_id = None
        try:
            data_file = document.dataFile
            if data_file is not None:
                data_file_id = data_file.id
        except Exception:
            # Unsaved documents raise instead of returning None here; treat
            # them as having no stable cloud identity.
            data_file_id = None
        return {"name": document.name, "data_file_id": data_file_id}

    def confirm(self, message):
        result = self._app().userInterface.messageBox(
            message,
            DIALOG_TITLE,
            adsk.core.MessageBoxButtonTypes.YesNoButtonType,
            adsk.core.MessageBoxIconTypes.QuestionIconType,
        )
        return result == adsk.core.DialogResults.DialogYes

    def choose_folder(self, title):
        dialog = self._app().userInterface.createFolderDialog()
        dialog.title = title
        if dialog.showDialog() != adsk.core.DialogResults.DialogOK:
            return None
        return dialog.folder

    def read_project_id(self):
        attribute = self._document().attributes.itemByName(ATTRIBUTE_GROUP, PROJECT_ID_ATTRIBUTE)
        if attribute is None:
            return None
        return attribute.value or None

    def write_project_id(self, project_id):
        self._document().attributes.add(ATTRIBUTE_GROUP, PROJECT_ID_ATTRIBUTE, project_id)

    def identity_records(self):
        """Return root-context occurrence/component identity data.

        Fusion entity objects are kept only as transient handles used by this
        process.  Persistent identity is always the UUID in the FMSM attribute.
        """
        design = self._app().activeProduct
        if design is None or not hasattr(design, "rootComponent"):
            raise RuntimeError("The active document does not contain a Fusion design.")
        records = []
        for occurrence in design.rootComponent.allOccurrences:
            component = occurrence.component
            records.append({
                "occurrence_handle": occurrence,
                "component_handle": component,
                "component_key": component.entityToken,
                "occurrence_id": self._attribute_value(occurrence, OCCURRENCE_ID_ATTRIBUTE),
                "component_id": self._attribute_value(component, COMPONENT_ID_ATTRIBUTE),
                "label": occurrence.name,
                "component_label": component.name,
                "part_number": component.partNumber,
            })
        return records

    @staticmethod
    def _attribute_value(entity, name):
        attribute = entity.attributes.itemByName(ATTRIBUTE_GROUP, name)
        return attribute.value if attribute is not None else None

    @staticmethod
    def write_occurrence_id(occurrence_handle, occurrence_id):
        occurrence_handle.attributes.add(ATTRIBUTE_GROUP, OCCURRENCE_ID_ATTRIBUTE, occurrence_id)

    @staticmethod
    def write_component_id(component_handle, component_id):
        component_handle.attributes.add(ATTRIBUTE_GROUP, COMPONENT_ID_ATTRIBUTE, component_id)
