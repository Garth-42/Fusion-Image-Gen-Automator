import json
import uuid

import fmsm.messaging.dispatcher as dispatcher_module
from fmsm.application.errors import ServiceError
from fmsm.messaging.dispatcher import MessageDispatcher
from fmsm.messaging.protocol import ALLOWED_ACTIONS, NULL_REQUEST_ID


def _request(action, payload=None):
    return json.dumps({
        "protocol_version": 1,
        "request_id": str(uuid.uuid4()),
        "action": action,
        "payload": payload if payload is not None else {},
    })


def test_project_actions_are_allowed():
    assert {
        "system.ping", "project.status", "project.initialize", "project.open",
        "identity.status", "identity.ensure_ids", "identity.repair_duplicates",
        "state.capture_current", "state.apply_captured", "state.restore", "preview.summary",
        "scene.list", "scene.get", "scene.load", "scene.create_from_current", "scene.update_metadata",
        "scene.update_state", "scene.duplicate", "scene.delete", "scene.reorder",
        "scene.render", "scene.render_all",
    } == set(ALLOWED_ACTIONS)


def test_registered_handler_receives_payload_and_answers():
    dispatcher = MessageDispatcher({"project.status": lambda payload: {"echo": payload}})
    response = dispatcher.dispatch(_request("project.status", {"a": 1}))
    assert response["ok"] is True
    assert response["result"] == {"echo": {"a": 1}}


def test_service_error_becomes_a_coded_error_response():
    def fail(payload):
        raise ServiceError("NO_ACTIVE_FUSION_DESIGN", "Open the assembly first.", {"hint": "open"})

    dispatcher = MessageDispatcher({"project.open": fail})
    response = dispatcher.dispatch(_request("project.open"))
    assert response["ok"] is False
    assert response["error"]["code"] == "NO_ACTIVE_FUSION_DESIGN"
    assert response["error"]["details"] == {"hint": "open"}


def test_allowed_action_without_handler_is_rejected():
    response = MessageDispatcher().dispatch(_request("project.status"))
    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_PALETTE_REQUEST"


def test_ping_round_trip():
    response = MessageDispatcher().dispatch(json.dumps({"protocol_version": 1, "request_id": str(uuid.uuid4()), "action": "system.ping", "payload": {}}))
    assert response["ok"] is True
    assert response["result"] == {"message": "pong"}


def test_unknown_action_is_rejected():
    response = MessageDispatcher().dispatch(json.dumps({"protocol_version": 1, "request_id": str(uuid.uuid4()), "action": "scene.write", "payload": {}}))
    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_PALETTE_REQUEST"


def test_malformed_json_is_answered_not_raised():
    response = MessageDispatcher().dispatch("{not json")
    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_PALETTE_REQUEST"
    assert response["request_id"] == NULL_REQUEST_ID


def test_unexpected_failure_is_answered_not_raised(monkeypatch):
    def explode(raw):
        raise RuntimeError("handler bug")

    monkeypatch.setattr(dispatcher_module, "parse_request", explode)

    # An exception escaping dispatch would leave the palette's request without
    # a returnData response — the exact silent-hang shape this add-in fixes.
    response = MessageDispatcher().dispatch("{}")
    assert response["ok"] is False
    assert response["error"]["code"] == "INTERNAL_ERROR"
    assert response["request_id"] == NULL_REQUEST_ID
    # The message must name the actual failure instead of an opaque catch-all,
    # and details must carry the traceback so a bug is diagnosable from the
    # palette rather than vanishing behind "unexpected error".
    assert "RuntimeError" in response["error"]["message"]
    assert "handler bug" in response["error"]["message"]
    details = response["error"]["details"]
    assert details["exception"] == "RuntimeError"
    assert details["detail"] == "handler bug"
    assert "RuntimeError" in details["traceback"]
