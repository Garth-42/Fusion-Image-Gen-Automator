"""Preview-document export for manual project scene summaries."""
from __future__ import absolute_import

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
        body_html = self._body_html(root, manifest)
        return {"html": self._html(manifest, body_html), "body_html": body_html, "title": manifest["project"]["title"]}

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

    def _body_html(self, root, manifest):
        project = manifest["project"]
        parts = [
            "<h1>%s</h1>" % _escape(project["title"]),
            "<p class=\"meta\">%d scene(s)</p>" % len(project["scenes"]),
        ]
        for index, entry in enumerate(project["scenes"], 1):
            parts.extend(self._scene_html(root, entry, index))
        return "\n".join(parts)

    def _scene_html(self, root, entry, index):
        scene = yaml_store.load(yaml_store.project_path(root, entry["file"]))
        issues = validate_scene(scene)
        if issues:
            issue = issues[0]
            raise ServiceError(issue.code, issue.message, {"path": issue.path, "scene_id": entry["scene_id"]})
        metadata = scene["scene"]
        output = scene.get("output") or {}
        return [
            "<article>",
            "<h2>%d. %s</h2>" % (index, _escape(metadata.get("title", "Untitled scene"))),
            "<p class=\"meta\">Status: %s | Scene ID: %s</p>" % (_escape(metadata.get("status", "draft")), _escape(entry["scene_id"])),
            _section("Description", metadata.get("description", "")),
            _section("Purpose", metadata.get("purpose", "")),
            _pre_section("Instructions", metadata.get("instructions_markdown", "")),
            "<p class=\"meta\">Image: %s<br>Thumbnail: %s</p>" % (_escape(output.get("image_file", "")), _escape(output.get("thumbnail_file", ""))),
            "</article>",
        ]


def _section(title, value):
    return "<h3>%s</h3><p>%s</p>" % (_escape(title), _escape(value or ""))


def _pre_section(title, value):
    return "<h3>%s</h3><pre>%s</pre>" % (_escape(title), _escape(value or ""))


def _escape(value):
    return html.escape(str(value), quote=True)
