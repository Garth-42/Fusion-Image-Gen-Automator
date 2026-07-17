import json
import uuid

from fmsm.messaging.dispatcher import MessageDispatcher


def test_ping_round_trip():
    response = MessageDispatcher().dispatch(json.dumps({"protocol_version": 1, "request_id": str(uuid.uuid4()), "action": "system.ping", "payload": {}}))
    assert response["ok"] is True
    assert response["result"] == {"message": "pong"}


def test_unknown_action_is_rejected():
    response = MessageDispatcher().dispatch(json.dumps({"protocol_version": 1, "request_id": str(uuid.uuid4()), "action": "scene.write", "payload": {}}))
    assert response["ok"] is False
    assert response["error"]["code"] == "INVALID_PALETTE_REQUEST"
