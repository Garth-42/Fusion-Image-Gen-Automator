"""Fusion implementation of the application-layer environment port."""
from __future__ import absolute_import

from pathlib import Path

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

    def _root_component(self):
        design = self._app().activeProduct
        if design is None or not hasattr(design, "rootComponent"):
            raise RuntimeError("The active document does not contain a Fusion design.")
        return design.rootComponent

    @staticmethod
    def _occurrence_opacity(occurrence):
        """Read one occurrence's own opacity override.

        Opacity overrides are per-occurrence and live on the component *proxy* in
        that occurrence's assembly context, not on the shared native component
        returned by ``occurrence.component``. Reading the native value misses
        instance overrides set in the browser, which is why captured opacity did
        not round-trip. ``visibleOpacity`` is the combined inherited result, not
        the occurrence's own override, so it is not used here.
        """
        return occurrence.component.createForAssemblyContext(occurrence).opacity

    @staticmethod
    def _set_occurrence_opacity(occurrence, opacity):
        occurrence.component.createForAssemblyContext(occurrence).opacity = opacity

    def _replay_transforms(self, occurrences, transforms, failure_message):
        """Apply occurrence transforms in one root-context batch.

        Setting ``transform2`` one occurrence at a time corrupts nested children:
        moving a parent rigidly drags its children, so a later per-child set
        fights that move. ``transformOccurrences`` flattens the assembly and
        applies every transform relative to the root at once, which is the
        documented way to replay nested occurrences (docs 8.3; ADR-0004).
        ``ignoreJoints=True`` because scenes position by transform, not joints.
        """
        if not occurrences:
            return
        if not self._root_component().transformOccurrences(occurrences, transforms, True):
            raise RuntimeError(failure_message)

    def identity_records(self):
        """Return root-context occurrence/component identity data.

        Fusion entity objects are kept only as transient handles used by this
        process.  Persistent identity is always the UUID in the FMSM attribute.
        """
        records = []
        for occurrence in self._root_component().allOccurrences:
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

    def capture_session_state(self, records=None):
        """Capture opaque live values for guarded restoration, not persistence."""
        if records is None:
            records = self.identity_records()
        viewport = self._app().activeViewport
        occurrences = []
        for record in records:
            occurrence = record["occurrence_handle"]
            occurrences.append((occurrence, occurrence.isLightBulbOn, occurrence.transform2.copy(), self._occurrence_opacity(occurrence)))
        return {"camera": viewport.camera, "occurrences": occurrences}

    def capture_scene_state(self):
        """Capture the current view as primitive data suitable for a scene file."""
        camera = self._app().activeViewport.camera
        success, width, height = camera.getExtents()
        if not success:
            raise RuntimeError("Fusion could not read the current camera extents.")
        camera_type = "orthographic" if camera.cameraType == adsk.core.CameraTypes.OrthographicCameraType else "perspective"
        records = self.identity_records()
        components = []
        seen_components = set()
        occurrences = []
        for record in records:
            occurrence = record["occurrence_handle"]
            occurrences.append({
                "occurrence_id": record["occurrence_id"], "label": record["label"],
                "part_number": record["part_number"], "visible": occurrence.isLightBulbOn,
                "opacity": self._occurrence_opacity(occurrence),
                "transform_matrix_cm": list(occurrence.transform2.asArray()),
            })
            if record["component_key"] not in seen_components:
                seen_components.add(record["component_key"])
                components.append({"component_id": record["component_id"], "label": record["component_label"]})
        return {
            "camera": {
                "type": camera_type,
                "eye_cm": [camera.eye.x, camera.eye.y, camera.eye.z],
                "target_cm": [camera.target.x, camera.target.y, camera.target.z],
                "up_vector": [camera.upVector.x, camera.upVector.y, camera.upVector.z],
                "extents_cm": {"width": width, "height": height} if camera_type == "orthographic" else None,
                "perspective_angle_rad": None if camera_type == "orthographic" else camera.perspectiveAngle,
                "is_fit_view": False,
            },
            "assembly_state": {"unlisted_occurrence_policy": "hide_and_warn", "occurrences": occurrences, "components": components},
        }

    def validate_scene_references(self, scene, records=None):
        if records is None:
            records = self.identity_records()
        occurrence_ids = {}
        component_ids = {}
        for record in records:
            occurrence_ids.setdefault(record["occurrence_id"], []).append(record)
        for record in self._unique_component_records(records):
            component_ids.setdefault(record["component_id"], []).append(record)
        issues = []
        for reference in scene["assembly_state"]["occurrences"]:
            self._reference_issue(issues, occurrence_ids, reference["occurrence_id"], reference["label"], "occurrence")
        for reference in scene["assembly_state"].get("components", []):
            self._component_reference_issue(issues, component_ids, reference["component_id"], reference["label"])
        return issues

    @staticmethod
    def _unique_component_records(records):
        unique = []
        seen = set()
        for record in records:
            key = record["component_key"]
            if key in seen:
                continue
            seen.add(key)
            unique.append(record)
        return unique

    @staticmethod
    def _reference_issue(issues, index, identifier, label, kind):
        matches = index.get(identifier, [])
        if not matches:
            issues.append({"code": "SCENE_REFERENCE_MISSING", "message": "Scene references a missing %s: %s." % (kind, label), "id": identifier, "label": label})
        elif len(matches) > 1:
            code = "DUPLICATE_%s_ID" % kind.upper()
            issues.append({"code": code, "message": "More than one current %s matches %s." % (kind, label), "id": identifier, "label": label})

    @staticmethod
    def _component_reference_issue(issues, index, identifier, label):
        matches = index.get(identifier, [])
        if not matches:
            return
        if len(matches) > 1:
            issues.append({"code": "DUPLICATE_COMPONENT_ID", "message": "More than one current component matches %s." % label, "id": identifier, "label": label})

    def apply_scene_state(self, scene, records=None):
        if records is None:
            records = self.identity_records()
        occurrences = {record["occurrence_id"]: record for record in records}
        present_components = set(record["component_id"] for record in records)
        # Scenes written before opacity moved onto occurrences stored it per
        # component; fall back to that so their authored look still replays.
        legacy_opacity = dict(
            (reference["component_id"], reference["opacity"])
            for reference in scene["assembly_state"].get("components", [])
            if reference.get("opacity") is not None
        )
        listed = set()
        move_occurrences = []
        move_transforms = []
        for reference in scene["assembly_state"]["occurrences"]:
            record = occurrences[reference["occurrence_id"]]
            occurrence = record["occurrence_handle"]
            matrix = adsk.core.Matrix3D.create()
            matrix.setWithArray(reference["transform_matrix_cm"])
            move_occurrences.append(occurrence)
            move_transforms.append(matrix)
            occurrence.isLightBulbOn = reference["visible"]
            opacity = reference.get("opacity")
            if opacity is None:
                opacity = legacy_opacity.get(record["component_id"], 1.0)
            self._set_occurrence_opacity(occurrence, opacity)
            listed.add(reference["occurrence_id"])
        self._replay_transforms(move_occurrences, move_transforms, "Fusion could not replay the scene occurrence transforms.")
        warnings = []
        for record in records:
            if record["occurrence_id"] not in listed:
                record["occurrence_handle"].isLightBulbOn = False
                warnings.append({"code": "UNLISTED_OCCURRENCE_HIDDEN", "label": record["label"]})
        for reference in scene["assembly_state"].get("components", []):
            if reference["component_id"] not in present_components:
                warnings.append({"code": "COMPONENT_REFERENCE_MISSING", "label": reference["label"]})
        self._apply_camera(scene["camera"])
        return {"warnings": warnings}

    def restore_session_state(self, snapshot):
        move_occurrences = []
        move_transforms = []
        for occurrence, visible, transform, opacity in snapshot["occurrences"]:
            occurrence.isLightBulbOn = visible
            self._set_occurrence_opacity(occurrence, opacity)
            move_occurrences.append(occurrence)
            move_transforms.append(transform)
        self._replay_transforms(move_occurrences, move_transforms, "Fusion could not restore the pre-scene occurrence transforms.")
        self._app().activeViewport.camera = snapshot["camera"]

    def refresh_viewport(self):
        self._app().activeViewport.refresh()

    def export_viewport_png(self, path, width_px, height_px, transparent_background, anti_alias):
        viewport = self._app().activeViewport
        if hasattr(viewport, "isBackgroundTransparent"):
            viewport.isBackgroundTransparent = transparent_background
        if hasattr(viewport, "isAntiAliasingEnabled"):
            viewport.isAntiAliasingEnabled = anti_alias
        if not viewport.saveAsImageFile(path, width_px, height_px):
            raise RuntimeError("Fusion did not save the viewport image.")
        # A True return is not proof of a file: exports into a read-only folder
        # have been observed to report success while writing nothing. Confirm the
        # file exists and is non-empty so the failure cannot pass silently.
        written = Path(path)
        if not written.is_file() or written.stat().st_size == 0:
            raise RuntimeError("Fusion reported a saved image but none was written to %s." % path)

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
