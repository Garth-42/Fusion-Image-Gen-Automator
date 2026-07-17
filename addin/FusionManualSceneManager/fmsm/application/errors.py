"""Failures with stable codes the palette can display (see docs/ERROR_CODES.md)."""
from __future__ import absolute_import


class ServiceError(Exception):
    def __init__(self, code, message, details=None):
        super(ServiceError, self).__init__(message)
        self.code = code
        self.message = message
        self.details = details if details is not None else {}
