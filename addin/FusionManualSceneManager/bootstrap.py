"""Fusion lifecycle and local palette setup."""
from __future__ import absolute_import

import os
import sys

ADDIN_ROOT = os.path.dirname(os.path.realpath(__file__))
if ADDIN_ROOT not in sys.path:
    sys.path.insert(0, ADDIN_ROOT)

from fmsm.fusion.palette_controller import PaletteController

_controller = None


def run(context):
    """Start the add-in and retain every Fusion event handler through its lifetime."""
    global _controller
    _controller = PaletteController(ADDIN_ROOT)
    _controller.start()


def stop(context):
    """Close UI resources; restoration is delegated to future state-guard wiring."""
    global _controller
    if _controller is not None:
        _controller.stop()
        _controller = None
