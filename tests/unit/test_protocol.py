import json
import uuid

import fmsm.messaging.dispatcher as dispatcher_module
from fmsm.messaging.dispatcher import MessageDispatcher
from fmsm.messaging.protocol import NULL_REQUEST_ID


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
