from __future__ import absolute_import

import os
import tempfile
from pathlib import Path


def atomic_write_text(destination, content):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=".%s." % destination.name, suffix=".tmp", dir=str(destination.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, str(destination))
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
