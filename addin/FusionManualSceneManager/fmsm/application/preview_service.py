"""Preview-document export for manual project scene summaries."""
from __future__ import absolute_import

import base64
import html

from fmsm.application import project_access
from fmsm.application.errors import ServiceError


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
        return project_access.require_project(self._fusion, self._settings, "previewing scenes")

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
        try:
            scene = project_access.load_scene(root, entry["file"])
        except ServiceError as error:
            details = dict(error.details)
            details["scene_id"] = entry["scene_id"]
            raise ServiceError(error.code, error.message, details)
        metadata = scene["scene"]
        output = scene.get("output") or {}
        return [
            "<article>",
            "<h2>%d. %s</h2>" % (index, _escape(metadata.get("title", "Untitled scene"))),
            "<p class=\"meta\">Status: %s | Scene ID: %s</p>" % (_escape(metadata.get("status", "draft")), _escape(entry["scene_id"])),
            self._image_html(root, output, "Rendered image"),
            _section("Description", metadata.get("description", "")),
            _section("Purpose", metadata.get("purpose", "")),
            _pre_section("Instructions", metadata.get("instructions_markdown", "")),
            "<p class=\"meta\">Image: %s<br>Thumbnail: %s</p>" % (_escape(output.get("image_file", "")), _escape(output.get("thumbnail_file", ""))),
            "</article>",
        ]


    def _image_html(self, root, output, alt):
        # Embed the thumbnail, not the final render. The preview is shown in a
        # palette a few hundred pixels wide, and every embedded byte crosses the
        # palette bridge as base64 inside one JSON message; full-size renders
        # made that message tens of megabytes for a modest project.
        for key in ("thumbnail_file", "image_file"):
            relative = output.get(key)
            if not relative:
                continue
            path = project_access.safe_path(root, relative)
            if not path.is_file():
                continue
            try:
                data = base64.b64encode(path.read_bytes()).decode("ascii")
            except OSError:
                continue
            return "<figure><img alt=\"%s\" src=\"data:image/png;base64,%s\" style=\"max-width:100%%;height:auto\"></figure>" % (_escape(alt), data)
        return ""


def _section(title, value):
    return "<h3>%s</h3><p>%s</p>" % (_escape(title), _escape(value or ""))


def _pre_section(title, value):
    return "<h3>%s</h3><pre>%s</pre>" % (_escape(title), _escape(value or ""))


def _escape(value):
    return html.escape(str(value), quote=True)
