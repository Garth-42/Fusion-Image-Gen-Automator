"""Fusion add-in entry point.

Fusion invokes ``run`` and ``stop`` from this file. Keep this boundary dependency-light:
it installs the add-in directory before importing local modules and reports every
bootstrap failure directly through Fusion's UI.
"""
from __future__ import absolute_import

import os
import sys
import traceback

import adsk.core


ADDIN_ROOT = os.path.dirname(os.path.realpath(__file__))


def _report_failure(operation, traceback_text):
    """Show errors that occur before the internal add-in modules can load."""
    app = adsk.core.Application.get()
    if app is not None:
        app.log("FMSM %s failed:\n%s" % (operation, traceback_text))
        ui = app.userInterface
        if ui is not None:
            ui.messageBox(
                "Fusion Manual Scene Manager could not %s.\n\n"
                "Open Fusion's Text Commands window and copy the FMSM traceback."
                % operation
            )


def _load_bootstrap():
    if ADDIN_ROOT not in sys.path:
        sys.path.insert(0, ADDIN_ROOT)
    import bootstrap
    return bootstrap


def run(context):
    try:
        _load_bootstrap().run(context)
    except Exception:
        _report_failure("start", traceback.format_exc())


def stop(context):
    try:
        _load_bootstrap().stop(context)
    except Exception:
        _report_failure("stop", traceback.format_exc())
