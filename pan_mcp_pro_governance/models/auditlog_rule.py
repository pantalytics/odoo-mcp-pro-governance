# Copyright 2026 Pantalytics B.V.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.http import request


class AuditlogRule(models.Model):
    _inherit = "auditlog.rule"

    x_scope = fields.Selection(
        selection=[
            ("all", "Log all requests"),
            ("browser", "Only browser sessions"),
            ("api", "Only API key calls"),
            ("users", "Specific users"),
        ],
        string="Scope",
        default="all",
        required=True,
        help=(
            "Which requests this rule applies to.\n"
            "- All: every request, browser and API.\n"
            "- Only browser sessions: cookie-authenticated requests, "
            "all users.\n"
            "- Only API key calls: requests authenticated by an API "
            "key. Optionally limit to specific keys.\n"
            "- Specific users: every request from these users — both "
            "their browser sessions and their API key calls."
        ),
    )
    x_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="x_auditlog_rule_user_rel",
        column1="rule_id",
        column2="user_id",
        string="Users to audit",
        help=(
            "Used when scope is 'Specific users'. Every request from "
            "these users is logged (browser + their API key calls)."
        ),
    )
    x_apikey_ids = fields.Many2many(
        comodel_name="res.users.apikeys",
        relation="x_auditlog_rule_apikey_rel",
        column1="rule_id",
        column2="apikey_id",
        string="API keys",
        help=(
            "Used when scope is 'Only API key calls'. Leave empty to "
            "log calls from every API key; fill to limit to specific "
            "keys."
        ),
    )

    @api.model
    def get_auditlog_fields(self, model):
        """Drop binary fields from the audited field set.

        A `log_type = full` rule snapshots every audited field of the
        record (`create_full` reads them one by one; `write_full` and
        `unlink_full` go through `read()`). For a Binary field declared
        with `attachment=True` — `stock.picking.signature`,
        `res.partner.image_1920`, every `fields.Image` — that read is
        not a column read: `Binary.read` resolves the value through
        `ir.attachment.search_fetch`, and a search flushes the model it
        searches.

        That flush is the bug. If the same transaction still holds a
        deferred write on `ir.attachment` — `documents_project` creating
        a document alongside a project, say — the flush cannot find the
        pending value in the cache and the ORM raises
        `AssertionError: Could not find all values of ir.attachment(N,)
        to flush them`, rolling back the whole transaction. Reported
        from production on Odoo 19 when confirming a sales order that
        creates a project and a delivery in one go.

        Reading an audited field must never touch another model, so the
        only reliable fix is to keep `ir.attachment` out of the audit
        path entirely. Flushing first does not help: the missing value
        is not in the cache either way.

        Excluding non-attachment binaries (plain `bytea` columns) too is
        deliberate. They cannot trigger the flush, but a base64 blob in
        a log line is not information anyone audits with — it just makes
        `auditlog_log_line` carry full file contents.

        `get_auditlog_fields` is OCA's documented override point and is
        shared by all three `_full` paths, so one override covers
        create, write and unlink. Upstream (OCA/server-tools 19.0) has
        no equivalent filter yet; this override can go once it does.
        Note that the rule's own `fields_to_exclude_ids` does not solve
        this — it is applied in `create_logs`, after the values have
        already been read.
        """
        fields_list = super().get_auditlog_fields(model)
        return [
            name
            for name in fields_list
            if getattr(model._fields.get(name), "type", None) != "binary"
        ]

    def _mcp_should_log_request(self, uid):
        """Whether a request from `uid` matches this rule's scope.

        `uid` is passed explicitly because `create_logs` runs sudo'd to
        bypass auditlog ACLs, which would make `self.env.uid` the
        superuser instead of the originator.
        """
        self.ensure_one()
        api_key_id = request.session.get("x_mcp_api_key_id") if request else None
        is_api = bool(api_key_id)
        scope = self.x_scope or "all"
        if scope == "all":
            return True
        if scope == "browser":
            return not is_api
        if scope == "api":
            if not is_api:
                return False
            if not self.x_apikey_ids:
                return True
            return api_key_id in self.x_apikey_ids.ids
        if scope == "users":
            return uid in self.x_user_ids.ids
        return True

    def create_logs(
        self,
        uid,
        res_model,
        res_ids,
        method,
        old_values=None,
        new_values=None,
        additional_log_values=None,
    ):
        model_id = self.pool._auditlog_model_cache.get(res_model)
        if model_id:
            rule = self.sudo().search([("model_id", "=", model_id)], limit=1)
            if rule and not rule._mcp_should_log_request(uid):
                return
        return super().create_logs(
            uid,
            res_model,
            res_ids,
            method,
            old_values=old_values,
            new_values=new_values,
            additional_log_values=additional_log_values,
        )
