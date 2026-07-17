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

    def capture_session_state(self):
        """Capture opaque live values for guarded restoration, not persistence."""
        viewport = self._app().activeViewport
        occurrences = []
        components = []
        seen_components = set()
        for record in self.identity_records():
            occurrence = record["occurrence_handle"]
            occurrences.append((occurrence, occurrence.isLightBulbOn, occurrence.transform2.copy()))
            key = record["component_key"]
            if key not in seen_components:
                seen_components.add(key)
                component = record["component_handle"]
                components.append((component, component.opacity))
        return {"camera": viewport.camera, "occurrences": occurrences, "components": components}

    def validate_scene_references(self, scene):
        records = self.identity_records()
        occurrence_ids = {}
        component_ids = {}
        for record in records:
            occurrence_ids.setdefault(record["occurrence_id"], []).append(record)
            component_ids.setdefault(record["component_id"], []).append(record)
        issues = []
        for reference in scene["assembly_state"]["occurrences"]:
            self._reference_issue(issues, occurrence_ids, reference["occurrence_id"], reference["label"], "occurrence")
        for reference in scene["assembly_state"].get("components", []):
            self._reference_issue(issues, component_ids, reference["component_id"], reference["label"], "component")
        return issues

    @staticmethod
    def _reference_issue(issues, index, identifier, label, kind):
        matches = index.get(identifier, [])
        if not matches:
            issues.append({"code": "SCENE_REFERENCE_MISSING", "message": "Scene references a missing %s: %s." % (kind, label), "id": identifier, "label": label})
        elif len(matches) > 1:
            code = "DUPLICATE_%s_ID" % kind.upper()
            issues.append({"code": code, "message": "More than one current %s matches %s." % (kind, label), "id": identifier, "label": label})

    def apply_scene_state(self, scene):
        records = self.identity_records()
        occurrences = {record["occurrence_id"]: record for record in records}
        components = {}
        for record in records:
            components.setdefault(record["component_id"], record)
        listed = set()
        for reference in scene["assembly_state"]["occurrences"]:
            record = occurrences[reference["occurrence_id"]]
            occurrence = record["occurrence_handle"]
            matrix = adsk.core.Matrix3D.create()
            matrix.setWithArray(reference["transform_matrix_cm"])
            occurrence.transform2 = matrix
            occurrence.isLightBulbOn = reference["visible"]
            listed.add(reference["occurrence_id"])
        warnings = []
        for record in records:
            if record["occurrence_id"] not in listed:
                record["occurrence_handle"].isLightBulbOn = False
                warnings.append({"code": "UNLISTED_OCCURRENCE_HIDDEN", "label": record["label"]})
        for reference in scene["assembly_state"].get("components", []):
            components[reference["component_id"]]["component_handle"].opacity = reference["opacity"]
        self._apply_camera(scene["camera"])
        return {"warnings": warnings}

    def restore_session_state(self, snapshot):
        for occurrence, visible, transform in snapshot["occurrences"]:
            occurrence.transform2 = transform
            occurrence.isLightBulbOn = visible
        for component, opacity in snapshot["components"]:
            component.opacity = opacity
        self._app().activeViewport.camera = snapshot["camera"]

    def refresh_viewport(self):
        self._app().activeViewport.refresh()

    def _apply_camera(self, camera_state):
        viewport = self._app().activeViewport
        camera = viewport.camera
        camera.eye = adsk.core.Point3D.create(*camera_state["eye_cm"])
        camera.target = adsk.core.Point3D.create(*camera_state["target_cm"])
        camera.upVector = adsk.core.Vector3D.create(*camera_state["up_vector"])
        camera.isFitView = False
        if camera_state["type"] == "orthographic":
            camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
            extents = camera_state["extents_cm"]
            camera.setExtents(extents["width"], extents["height"])
        else:
            camera.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
            camera.perspectiveAngle = camera_state["perspective_angle_rad"]
        viewport.camera = camera
