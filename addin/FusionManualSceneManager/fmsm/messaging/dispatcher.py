from __future__ import absolute_import

from fmsm.application.errors import ServiceError
from fmsm.messaging.protocol import (
    NULL_REQUEST_ID,
    ProtocolError,
    parse_request,
    response,
)


class MessageDispatcher(object):
    """Route palette requests to the injected action handlers.

    ``dispatch`` must never raise: an unanswered request leaves the palette
    waiting on a response that will never arrive, so every failure — including
    an unexpected one — is converted into an error response the page can show.
    """

    def __init__(self, handlers=None):
        self._handlers = dict(handlers or {})

    def dispatch(self, raw):
        request_id = None
        try:
            request = parse_request(raw)
            request_id = request["request_id"]
            action = request["action"]
            if action == "system.ping":
                return response(request_id, {"message": "pong"})
            handler = self._handlers.get(action)
            if handler is None:
                return self._error(request_id, "INVALID_PALETTE_REQUEST", "Unhandled action.")
            return response(request_id, handler(request["payload"]))
        except ProtocolError as error:
            return self._error(request_id, "INVALID_PALETTE_REQUEST", str(error))
        except ServiceError as error:
            return self._error(request_id, error.code, error.message, error.details)
        except Exception:
            return self._error(
                request_id, "INTERNAL_ERROR", "Unexpected add-in error while handling the request."
            )

    @staticmethod
    def _error(request_id, code, message, details=None):
        return response(
            request_id or NULL_REQUEST_ID,
            error={"code": code, "message": message, "details": details if details is not None else {}},
        )
