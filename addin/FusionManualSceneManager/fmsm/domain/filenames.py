from __future__ import absolute_import

import re
import unicodedata

_MAX_SLUG_LENGTH = 60


def slugify(title):
    normalized = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub("[^a-z0-9]+", "-", normalized).strip("-")
    # Titles may be 200 characters; a file name that long, under a deep project
    # folder, runs into Windows' path-length limit.
    slug = slug[:_MAX_SLUG_LENGTH].strip("-")
    return slug or "scene"


def scene_basename(title, scene_id):
    return "%s__%s" % (slugify(title), str(scene_id).replace("-", "")[:8])
