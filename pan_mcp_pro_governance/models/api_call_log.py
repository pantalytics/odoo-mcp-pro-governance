from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class McpGovernanceApiCallLog(models.Model):
    """Append-only log of inbound MCP / API calls.

    One row per HTTP request that hits the MCP endpoint. Correlated to
    `mcp.governance.audit.log` entries via `x_request_id` — one call may
    produce zero or more ORM-level audit rows.

    Like the audit log, rows are immutable once written.
    """

    _name = "mcp.governance.api.call.log"
    _description = "MCP Governance API Call Log"
    _order = "create_date desc, id desc"
    _rec_name = "display_name"

    x_agent_identity_id = fields.Many2one(
        "mcp.governance.agent.identity",
        string="Agent",
        ondelete="restrict",
        index=True,
    )
    x_user_id = fields.Many2one(
        "res.users",
        string="Acting User",
        index=True,
    )
    x_request_id = fields.Char(
        index=True,
        string="Request ID",
        help="Correlation id from the MCP call. Joins to mcp.governance.audit.log.",
    )
    x_method = fields.Selection(
        selection=[
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
            ("PATCH", "PATCH"),
            ("DELETE", "DELETE"),
            ("OTHER", "Other"),
        ],
        default="POST",
        required=True,
        index=True,
        string="Method",
    )
    x_path = fields.Char(string="Path", help="Request path, e.g. /mcp/tools/call.")
    x_tool_name = fields.Char(
        index=True,
        string="Tool",
        help="MCP tool invoked, when applicable (e.g. search_records).",
    )
    x_status_code = fields.Integer(string="Status", index=True)
    x_duration_ms = fields.Integer(string="Duration (ms)")
    x_request_bytes = fields.Integer(string="Request Size")
    x_response_bytes = fields.Integer(string="Response Size")
    x_ip_address = fields.Char(string="IP Address")
    x_error_message = fields.Text(string="Error")

    x_audit_log_ids = fields.Many2many(
        comodel_name="mcp.governance.audit.log",
        compute="_compute_audit_log_ids",
        string="Related Audit Entries",
    )
    x_audit_log_count = fields.Integer(compute="_compute_audit_log_ids")

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("x_method", "x_path", "x_tool_name", "x_status_code")
    def _compute_display_name(self):
        for rec in self:
            head = rec.x_tool_name or rec.x_path or "?"
            rec.display_name = f"{rec.x_method} {head} → {rec.x_status_code or '-'}"

    @api.depends("x_request_id")
    def _compute_audit_log_ids(self):
        AuditLog = self.env["mcp.governance.audit.log"]
        for rec in self:
            if rec.x_request_id:
                rec.x_audit_log_ids = AuditLog.search([("x_request_id", "=", rec.x_request_id)])
            else:
                rec.x_audit_log_ids = AuditLog.browse()
            rec.x_audit_log_count = len(rec.x_audit_log_ids)

    def action_open_audit_log(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Audit entries for %s", self.display_name),
            "res_model": "mcp.governance.audit.log",
            "view_mode": "list,form",
            "domain": [("x_request_id", "=", self.x_request_id)],
        }

    def write(self, vals):
        raise AccessError(_("API call log entries are immutable."))

    def unlink(self):
        raise AccessError(_("API call log entries cannot be deleted."))
