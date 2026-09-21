# Copyright 2026 Pantalytics B.V.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re

from odoo import _, api, fields, models
from odoo.http import request

from .ir_http import (
    current_request_api_key_id,
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

    # NOTE — this many2one can dangle. `res.users.apikeys` is `_auto = False`,
    # so Odoo skips the foreign key for it (`Many2one.update_db_foreign_key`
    # bails out on a comodel without `_auto`), which means no `ondelete` rule
    # can ever fire. Revoking a key runs a raw `DELETE FROM res_users_apikeys`
    # in core's `_remove()`, leaving this column pointing at a row that is
    # gone; rendering it then raises MissingError. Keep it for domains and
    # back-compat, but display the x_api_key_ref / x_api_key_name snapshot
    # below instead. See issue #28.
    x_api_key_id = fields.Many2one(
        comodel_name="res.users.apikeys",
        string="API Key (link)",
        index=True,
        readonly=True,
        help="The API key used to authenticate this request, if any. "
        "Empty for requests made through a browser session (cookie auth). "
        "May point at a key that has since been revoked — the audit trail "
        "reads the API Key / API Key ID snapshot instead.",
    )
    x_api_key_ref = fields.Integer(
        string="API Key ID",
        index=True,
        readonly=True,
        help="Database id the API key had when this request was logged. "
        "Stored as a plain integer so it survives revocation of the key.",
    )
    x_api_key_name = fields.Char(
        string="API Key",
        readonly=True,
        help="Description the API key carried when this request was logged. "
        "Stored as text so the audit trail stays readable after the key "
        "is revoked.",
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
        # Reads the live request when available, else the ir.http._dispatch
        # snapshot (legacy /jsonrpc and /xmlrpc lose the request inside
        # dispatch_rpc). Shared with the audit-rule scope filter.
        api_key_id = current_request_api_key_id()
        if api_key_id:
            # Snapshot the key identity as plain data in the same breath:
            # the many2one above outlives the key row it points at.
            api_key_name = self._mcp_api_key_name(api_key_id)
            for vals in vals_list:
                vals.setdefault("x_api_key_id", api_key_id)
                vals.setdefault("x_api_key_ref", api_key_id)
                vals.setdefault("x_api_key_name", api_key_name)
        return super().create(vals_list)

    @api.model
    def _mcp_api_key_name(self, api_key_id):
        """Description of ``api_key_id``, or a stable fallback label.

        sudo: the audit row must record the key that authenticated the
        request even when the acting user cannot read that key row.
        """
        key = self.env["res.users.apikeys"].sudo().browse(api_key_id).exists()
        return key.name or _("API key #%s", api_key_id)

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
