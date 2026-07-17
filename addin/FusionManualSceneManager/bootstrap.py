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
    try:
        _controller = PaletteController(ADDIN_ROOT)
        _controller.start()
    except Exception:
        _controller = None
        report_startup_failure(traceback.format_exc())


def stop(context):
    """Close UI resources; restoration is delegated to future state-guard wiring."""
    global _controller
    if _controller is not None:
        _controller.stop()
        _controller = None
