from __future__ import absolute_import

import os
import tempfile
from pathlib import Path


def staging_path(destination):
    """Return the sibling path a write to *destination* is staged through.

    Deliberately in the destination's own directory: staging elsewhere and
    copying in would answer "can the temp directory be written?" instead of
    "can this output folder be written?", which is the question a blocked
    render needs answered. The process id keeps two Fusion sessions sharing one
    project folder from staging onto each other's file, and the suffix is kept
    last so a consumer that infers a format from the extension still sees one.

    Not hidden behind a leading dot, unlike the YAML temporary below. Fusion
    writes this file itself, so it is worth keeping the name to shapes any
    exporter handles; and one orphaned by a crash mid-render should be visible
    to whoever has to clean it up rather than invisible in Finder.
    """
    destination = Path(destination)
    return destination.with_name("%s.fmsm-staging-%d%s" % (destination.stem, os.getpid(), destination.suffix))


def commit(staging, destination):
    """Move a completed staging file onto its destination."""
    os.replace(str(staging), str(destination))


def discard(staging):
    """Remove a staging file, if one is still there, without raising."""
    try:
        os.unlink(str(staging))
    except OSError:
        pass


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
