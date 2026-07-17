from __future__ import absolute_import

import re
import unicodedata


def slugify(title):
    normalized = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub("[^a-z0-9]+", "-", normalized).strip("-")
    return slug or "scene"


def scene_basename(title, scene_id):
    return "%s__%s" % (slugify(title), str(scene_id).replace("-", "")[:8])
