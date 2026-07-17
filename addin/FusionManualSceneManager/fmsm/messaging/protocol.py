"""Versioned, allow-listed messages exchanged with the local palette."""
from __future__ import absolute_import

import json
import uuid

PROTOCOL_VERSION = 1
ALLOWED_ACTIONS = frozenset(["system.ping"])


class ProtocolError(ValueError):
    pass


def parse_request(raw):
    try:
        request = json.loads(raw)
    except (TypeError, ValueError):
        raise ProtocolError("Message must be valid JSON.")
    if not isinstance(request, dict):
        raise ProtocolError("Message must be an object.")
    if request.get("protocol_version") != PROTOCOL_VERSION:
        raise ProtocolError("Unsupported protocol version.")
    request_id = request.get("request_id")
    try:
        uuid.UUID(request_id)
    except (TypeError, ValueError, AttributeError):
        raise ProtocolError("request_id must be a UUID.")
    action = request.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ProtocolError("Action is not allowed.")
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise ProtocolError("payload must be an object.")
    return request


def response(request_id, result=None, error=None):
    base = {"protocol_version": PROTOCOL_VERSION, "request_id": request_id}
    if error is None:
        base.update({"ok": True, "result": result if result is not None else {}})
    else:
        base.update({"ok": False, "error": error})
    return base
