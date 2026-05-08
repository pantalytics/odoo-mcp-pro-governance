from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class McpGovernanceAuditLog(models.Model):
    """Append-only audit log for MCP / AI agent activity.

    Records are immutable once written: the only way to amend the trail
    is to add another entry. Even the manager group cannot edit or
    delete existing rows — enforced in `write` and `unlink`.
    """

    _name = "mcp.governance.audit.log"
    _description = "MCP Governance Audit Log"
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
        help="The Odoo user under whose credentials the action ran.",
    )
    x_action = fields.Selection(
        selection=[
            ("read", "Read"),
            ("create", "Create"),
            ("update", "Update"),
            ("delete", "Delete"),
            ("execute", "Execute"),
            ("login", "Login"),
            ("other", "Other"),
        ],
        required=True,
        default="other",
        index=True,
        string="Action",
    )
    x_model_id = fields.Many2one("ir.model", string="Model", ondelete="set null")
    x_res_id = fields.Integer(string="Record ID")
    x_description = fields.Text(string="Description")
    x_request_id = fields.Char(
        index=True,
        string="Request ID",
        help="Correlation id from the MCP call (e.g. HTTP request id).",
    )
    x_prompt_hash = fields.Char(
        string="Prompt Hash",
        help="SHA-256 of the prompt that drove this action, if available. "
        "The prompt itself is not stored here by default.",
    )
    x_ip_address = fields.Char(string="IP Address")

    display_name = fields.Char(compute="_compute_display_name", store=True)

    @api.depends("x_action", "x_model_id", "x_res_id", "x_agent_identity_id")
    def _compute_display_name(self):
        for rec in self:
            parts = [rec.x_action or "?"]
            if rec.x_model_id:
                parts.append(rec.x_model_id.model)
            if rec.x_res_id:
                parts.append(f"#{rec.x_res_id}")
            if rec.x_agent_identity_id:
                parts.append(f"by {rec.x_agent_identity_id.name}")
            rec.display_name = " ".join(parts)

    def write(self, vals):
        raise AccessError(_("Audit log entries are immutable."))

    def unlink(self):
        raise AccessError(_("Audit log entries cannot be deleted."))
