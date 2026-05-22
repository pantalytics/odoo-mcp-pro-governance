"""Per-request thread-local maintenance.

Two responsibilities:

1. Clear the API-key role thread-local at the start of every request, so a
   role-bound key request cannot leak its narrowing into a UI session that
   reuses the same worker thread.

2. Snapshot the werkzeug request context so the auditlog HTTP request /
   session capture still works for the legacy ``/jsonrpc`` and ``/xmlrpc``
   endpoints. Odoo's ``dispatch_rpc()`` wraps those services in
   ``borrow_request()`` (odoo/http.py:1412), which pops the request off the
   threadlocal stack for the duration of the dispatch. By that point the
   patched ORM methods that drive auditlog can no longer see the request.
   We capture what auditlog needs *before* ``_dispatch`` returns and expose
   it via :func:`get_audit_request_snapshot`.
"""

import threading

from odoo import models
from odoo.http import request as http_request

from .res_users_apikeys import clear_thread_api_key_role_id

_audit_local = threading.local()


def _snapshot_from_request():
    if not http_request:
        return None
    try:
        httprequest = http_request.httprequest
        session = http_request.session
    except Exception:
        return None
    return {
        "path": httprequest.path if httprequest else None,
        "url_root": httprequest.url_root if httprequest else None,
        "session_sid": session.sid if session else None,
        "api_key_id": session.get("x_mcp_api_key_id") if session else None,
        "uid": http_request.env.uid if http_request.env else None,
    }


def get_audit_request_snapshot():
    """Return the captured request context, or ``None`` if not set."""
    return getattr(_audit_local, "snapshot", None)


def set_audit_api_key_id(value):
    """Stash the authenticated API key id on the thread-local snapshot.

    Called from ``res.users.apikeys._check_credentials`` once the key has
    been resolved. Necessary for the legacy /jsonrpc and /xmlrpc paths
    where the werkzeug request has already been popped by
    ``borrow_request()`` so we cannot push it onto ``request.session``.
    """
    snapshot = getattr(_audit_local, "snapshot", None)
    if snapshot is not None:
        snapshot["api_key_id"] = value


def get_audit_cached_request_id():
    return getattr(_audit_local, "http_request_id", None)


def set_audit_cached_request_id(value):
    _audit_local.http_request_id = value


def get_audit_cached_session_id():
    return getattr(_audit_local, "http_session_id", None)


def set_audit_cached_session_id(value):
    _audit_local.http_session_id = value


def _clear_audit_locals():
    for attr in ("snapshot", "http_request_id", "http_session_id"):
        if hasattr(_audit_local, attr):
            delattr(_audit_local, attr)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _dispatch(cls, endpoint):
        clear_thread_api_key_role_id()
        _clear_audit_locals()
        _audit_local.snapshot = _snapshot_from_request()
        try:
            return super()._dispatch(endpoint)
        finally:
            _clear_audit_locals()
