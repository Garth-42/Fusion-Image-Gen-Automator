"""Fusion implementation of the application-layer environment port."""
from __future__ import absolute_import

import adsk.core

from fmsm.application.ports import FusionEnvironmentPort

ATTRIBUTE_GROUP = "FMSM"
PROJECT_ID_ATTRIBUTE = "project_id"
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
