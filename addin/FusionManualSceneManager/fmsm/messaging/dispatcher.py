from __future__ import absolute_import

from fmsm.messaging.protocol import ProtocolError, parse_request, response


class MessageDispatcher(object):
    def dispatch(self, raw):
        request_id = None
        try:
            request = parse_request(raw)
            request_id = request["request_id"]
            if request["action"] == "system.ping":
                return response(request_id, {"message": "pong"})
        except ProtocolError as error:
            return response(request_id or "00000000-0000-0000-0000-000000000000", error={
                "code": "INVALID_PALETTE_REQUEST", "message": str(error), "details": {}})
        return response(request_id, error={"code": "INVALID_PALETTE_REQUEST", "message": "Unhandled action.", "details": {}})
