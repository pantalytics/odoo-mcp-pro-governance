# Copyright 2026 Pantalytics B.V.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AuditlogLog(models.Model):
    _inherit = "auditlog.log"

    x_api_key_id = fields.Many2one(
        related="http_request_id.x_api_key_id",
        comodel_name="res.users.apikeys",
        string="API Key",
        store=True,
        index=True,
        readonly=True,
        help="The API key used to authenticate the originating request, if any.",
    )
