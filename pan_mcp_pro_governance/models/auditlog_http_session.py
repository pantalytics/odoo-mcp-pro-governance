# Copyright 2026 Pantalytics B.V.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.http import request

from .ir_http import (
    get_audit_cached_session_id,
    get_audit_request_snapshot,
    set_audit_cached_session_id,
)


class AuditlogHTTPSession(models.Model):
    _inherit = "auditlog.http.session"

    @api.model
    def current_http_session(self):
        if request:
            return super().current_http_session()

        snapshot = get_audit_request_snapshot()
        if not snapshot:
            return False

        sid = snapshot.get("session_sid")
        if not sid:
            return False
        uid = snapshot.get("uid") or self.env.uid

        cached = get_audit_cached_session_id()
        if cached:
            self.env.cr.execute(
                "SELECT id FROM auditlog_http_session WHERE id = %s",
                (cached,),
            )
            if self.env.cr.fetchone():
                return cached

        existing = self.search([("name", "=", sid), ("user_id", "=", uid)], limit=1)
        if existing:
            set_audit_cached_session_id(existing.id)
            return existing.id

        new_id = self.create({"name": sid, "user_id": uid}).id
        set_audit_cached_session_id(new_id)
        return new_id
