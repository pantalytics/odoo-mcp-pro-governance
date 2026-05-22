# Copyright 2026 Pantalytics B.V.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import api, fields, models
from odoo.http import request

from .ir_http import (
    get_audit_cached_request_id,
    get_audit_request_snapshot,
    set_audit_cached_request_id,
)

# Matches Odoo RPC paths where the model + method are the last two
# segments: /web/dataset/call_kw/<model>/<method> (web client) and
# /json/2/<model>/<method> (modern bearer-auth API used by MCP).
_RPC_PATH_RE = re.compile(r"^/(?:web/dataset/call_kw|json/2)/([\w.]+)/(\w+)/?$")


class AuditlogHTTPRequest(models.Model):
    _inherit = "auditlog.http.request"

    x_api_key_id = fields.Many2one(
        comodel_name="res.users.apikeys",
        string="API Key",
        index=True,
        ondelete="set null",
        readonly=True,
        help="The API key used to authenticate this request, if any. "
        "Empty for requests made through a browser session (cookie auth).",
    )
    x_model = fields.Char(
        string="Model",
        compute="_compute_x_model_method",
        help="Odoo model invoked by this request, parsed from the path.",
    )
    x_method = fields.Char(
        string="Method",
        compute="_compute_x_model_method",
        help="ORM method invoked by this request, parsed from the path.",
    )

    @api.depends("name")
    def _compute_x_model_method(self):
        for req in self:
            match = _RPC_PATH_RE.match(req.name or "")
            req.x_model = match.group(1) if match else False
            req.x_method = match.group(2) if match else False

    @api.model_create_multi
    def create(self, vals_list):
        # Read api_key_id from the live request when available, otherwise
        # fall back to the snapshot captured in ir.http._dispatch (legacy
        # /jsonrpc and /xmlrpc lose the request inside dispatch_rpc).
        api_key_id = None
        if request:
            api_key_id = request.session.get("x_mcp_api_key_id")
        else:
            snapshot = get_audit_request_snapshot()
            if snapshot:
                api_key_id = snapshot.get("api_key_id")
        if api_key_id:
            for vals in vals_list:
                vals.setdefault("x_api_key_id", api_key_id)
        return super().create(vals_list)

    @api.model
    def current_http_request(self):
        # Fast path: when werkzeug request is bound (UI + modern /json/2),
        # defer entirely to OCA's implementation, which also caches the id
        # on the httprequest object so repeated calls reuse it.
        if request:
            return super().current_http_request()

        # Legacy /jsonrpc and /xmlrpc dispatch through borrow_request(),
        # which unsets the werkzeug threadlocal. Fall back to the snapshot
        # taken in ir.http._dispatch, and cache the created row id on our
        # own thread-local for the duration of the request.
        snapshot = get_audit_request_snapshot()
        if not snapshot:
            return False

        cached = get_audit_cached_request_id()
        if cached:
            self.env.cr.execute(
                "SELECT id FROM auditlog_http_request WHERE id = %s",
                (cached,),
            )
            if self.env.cr.fetchone():
                return cached

        http_session_model = self.env["auditlog.http.session"]
        vals = {
            "name": snapshot.get("path"),
            "root_url": snapshot.get("url_root"),
            "user_id": snapshot.get("uid") or self.env.uid,
            "http_session_id": http_session_model.current_http_session(),
            "user_context": str(dict(self.env.context)),
        }
        new_id = self.create(vals).id
        set_audit_cached_request_id(new_id)
        return new_id
