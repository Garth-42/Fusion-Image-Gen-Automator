from __future__ import absolute_import

from fmsm.messaging.protocol import (
    NULL_REQUEST_ID,
    ProtocolError,
    parse_request,
    response,
)


class MessageDispatcher(object):
    """Answer palette requests.

    ``dispatch`` must never raise: an unanswered request leaves the palette
    waiting on a response that will never arrive, so every failure — including
    an unexpected one — is converted into an error response the page can show.
    """

    def dispatch(self, raw):
        request_id = None
        try:
            request = parse_request(raw)
            request_id = request["request_id"]
            if request["action"] == "system.ping":
                return response(request_id, {"message": "pong"})
            return self._error(request_id, "INVALID_PALETTE_REQUEST", "Unhandled action.")
        except ProtocolError as error:
            return self._error(request_id, "INVALID_PALETTE_REQUEST", str(error))
        except Exception:
            return self._error(
                request_id, "INTERNAL_ERROR", "Unexpected add-in error while handling the request."
            )

    @staticmethod
    def _error(request_id, code, message):
        return response(
            request_id or NULL_REQUEST_ID,
            error={"code": code, "message": message, "details": {}},
        )
