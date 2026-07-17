"""Fusion lifecycle and local palette setup."""
from __future__ import absolute_import

import os
import sys
import traceback

ADDIN_ROOT = os.path.dirname(os.path.realpath(__file__))
if ADDIN_ROOT not in sys.path:
    sys.path.insert(0, ADDIN_ROOT)

from fmsm.fusion.palette_controller import PaletteController, report_startup_failure

_controller = None


def run(context):
    """Start the add-in and surface initialization failures to the Fusion user."""
    global _controller
    controller = PaletteController()
    try:
        controller.start()
    except Exception:
        # Tear down whatever the failed start managed to create. A palette that
        # outlives its failed run would be picked up by the next start as a
        # stale, unresponsive page.
        try:
            controller.stop()
        except Exception:
            pass
        report_startup_failure(traceback.format_exc())
        return
    _controller = controller


def stop(context):
    """Close UI resources; restoration is delegated to future state-guard wiring."""
    global _controller
    if _controller is not None:
        _controller.stop()
        _controller = None
