# Copyright 2026 Pantalytics B.V.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.http import request


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

    @api.model_create_multi
    def create(self, vals_list):
        if request:
            api_key_id = request.session.get("x_mcp_api_key_id")
            if api_key_id:
                for vals in vals_list:
                    vals.setdefault("x_api_key_id", api_key_id)
        return super().create(vals_list)
