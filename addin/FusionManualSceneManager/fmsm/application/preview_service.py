"""Preview-document export for manual project scene summaries."""
from __future__ import absolute_import

import base64
import html
from pathlib import Path

from fmsm.application.errors import ServiceError
from fmsm.application.services import MANIFEST_FILE
from fmsm.domain.validation import validate_manifest, validate_scene
from fmsm.infrastructure import yaml_store


class PreviewService(object):
    """Build a small HTML preview of scene metadata from project YAML."""

    def __init__(self, fusion, settings):
        self._fusion = fusion
        self._settings = settings

    def handlers(self):
        return {"preview.summary": self.summary}

    def summary(self, payload):
        root, manifest = self._require_project()
        scenes = self._scenes(root, manifest)
        # The palette gets thumbnails, the exportable document gets the full
        # renders. Both were built from the 2400x1600 images, which reach the
        # palette as base64 inside ``innerHTML`` — megabytes per scene, and a
        # scene whose picture never appeared at all was the first symptom
        # (round-4 S5.5). A 480x320 thumbnail is what this preview shows anyway.
        return {
            "html": self._html(manifest, self._body_html(root, manifest, scenes, prefer_thumbnail=False)),
            "body_html": self._body_html(root, manifest, scenes, prefer_thumbnail=True),
            "title": manifest["project"]["title"],
        }

    def _require_project(self):
        document = self._fusion.active_document()
        if document is None:
            raise ServiceError("NO_ACTIVE_FUSION_DESIGN", "Open the documentation assembly before previewing scenes.")
        project_id = self._fusion.read_project_id()
        if project_id is None:
            raise ServiceError("PROJECT_NOT_OPEN", "Initialize or open a manual project before previewing scenes.")
        root = self._settings.project_root(project_id)
        if root is None or not (Path(root) / MANIFEST_FILE).is_file():
            raise ServiceError("PROJECT_ROOT_UNRESOLVED", "Open the manual project folder before previewing scenes.")
        manifest = yaml_store.load(Path(root) / MANIFEST_FILE)
        issues = validate_manifest(manifest)
        if issues:
            issue = issues[0]
            raise ServiceError(issue.code, issue.message, {"path": issue.path})
        return root, manifest

    def _html(self, manifest, body_html):
        return "\n".join([
            "<!doctype html>",
            "<html><head><meta charset=\"utf-8\">",
            "<title>%s</title>" % _escape(manifest["project"]["title"]),
            "<style>body{font-family:sans-serif;margin:24px;line-height:1.4}article{border-top:1px solid #ccc;padding:16px 0}h1{margin-top:0}.meta{color:#555}pre{white-space:pre-wrap;background:#f6f6f6;padding:8px}</style>",
            "</head><body>",
            body_html,
            "</body></html>",
        ])

    def _scenes(self, root, manifest):
        """Load and validate every scene once, for both renderings below."""
        scenes = []
        for entry in manifest["project"]["scenes"]:
            scene = yaml_store.load(yaml_store.project_path(root, entry["file"]))
            issues = validate_scene(scene)
            if issues:
                issue = issues[0]
                raise ServiceError(issue.code, issue.message, {"path": issue.path, "scene_id": entry["scene_id"]})
            scenes.append((entry, scene))
        return scenes

    def _body_html(self, root, manifest, scenes, prefer_thumbnail):
        project = manifest["project"]
        parts = [
            "<h1>%s</h1>" % _escape(project["title"]),
            "<p class=\"meta\">%d scene(s)</p>" % len(project["scenes"]),
        ]
        for index, (entry, scene) in enumerate(scenes, 1):
            parts.extend(self._scene_html(root, entry, scene, index, prefer_thumbnail))
        return "\n".join(parts)

    def _scene_html(self, root, entry, scene, index, prefer_thumbnail):
        metadata = scene["scene"]
        output = scene.get("output") or {}
        return [
            "<article>",
            "<h2>%d. %s</h2>" % (index, _escape(metadata.get("title", "Untitled scene"))),
            "<p class=\"meta\">Status: %s | Scene ID: %s</p>" % (_escape(metadata.get("status", "draft")), _escape(entry["scene_id"])),
            self._image_html(root, output, "Rendered image", prefer_thumbnail),
            _section("Description", metadata.get("description", "")),
            _section("Purpose", metadata.get("purpose", "")),
            _pre_section("Instructions", metadata.get("instructions_markdown", "")),
            "<p class=\"meta\">Image: %s<br>Thumbnail: %s</p>" % (_escape(output.get("image_file", "")), _escape(output.get("thumbnail_file", ""))),
            "</article>",
        ]

    def _image_html(self, root, output, alt, prefer_thumbnail):
        candidates = [output.get("image_file", "")]
        if prefer_thumbnail:
            # Fall back to the full render: a scene can carry a final image with
            # no thumbnail, and showing nothing would read as a failed render.
            candidates.insert(0, output.get("thumbnail_file", ""))
        for relative in candidates:
            if not relative:
                continue
            path = yaml_store.project_path(root, relative)
            if not path.is_file():
                continue
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            return "<figure><img alt=\"%s\" src=\"data:image/png;base64,%s\" style=\"max-width:100%%;height:auto\"></figure>" % (_escape(alt), data)
        return ""


def _section(title, value):
    return "<h3>%s</h3><p>%s</p>" % (_escape(title), _escape(value or ""))


def _pre_section(title, value):
    return "<h3>%s</h3><pre>%s</pre>" % (_escape(title), _escape(value or ""))


def _escape(value):
    return html.escape(str(value), quote=True)
