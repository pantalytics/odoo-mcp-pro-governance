# Copyright 2026 Pantalytics B.V.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AuditlogLog(models.Model):
    _inherit = "auditlog.log"

    # See the NOTE on auditlog.http.request.x_api_key_id: this many2one can
    # point at a revoked key, and rendering it then raises MissingError. Kept
    # for domains (the API only / Browser only filters never read the target
    # row) and for rows logged before the snapshot existed; the views show
    # x_api_key_name / x_api_key_ref instead. See issue #28.
    x_api_key_id = fields.Many2one(
        related="http_request_id.x_api_key_id",
        comodel_name="res.users.apikeys",
        string="API Key (link)",
        store=True,
        index=True,
        readonly=True,
        help="The API key used to authenticate the originating request, if any. "
        "May point at a key that has since been revoked — the audit trail "
        "reads the API Key / API Key ID snapshot instead.",
    )
    x_api_key_ref = fields.Integer(
        related="http_request_id.x_api_key_ref",
        string="API Key ID",
        store=True,
        index=True,
        readonly=True,
        help="Database id the API key had when the originating request was "
        "logged. Stored as a plain integer so it survives revocation.",
    )
    x_api_key_name = fields.Char(
        related="http_request_id.x_api_key_name",
        string="API Key",
        store=True,
        readonly=True,
        help="Description the API key carried when the originating request "
        "was logged. Stored as text so the audit trail stays readable after "
        "the key is revoked.",
    )
