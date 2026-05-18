from odoo import _, api, fields, models


class McpGovernanceAgentIdentity(models.Model):
    """First-class identity for every AI agent that talks to Odoo.

    The agent binds to a technical `res.users` record — its ACLs and record
    rules govern what the agent can actually do. Inbound HTTP calls made by
    that user are logged by OCA `auditlog` and surfaced here via the
    "API Calls" smart button.

    Future governance features (policies, quotas, risk class, approval
    workflows) attach to this model.
    """

    _name = "mcp.governance.agent.identity"
    _description = "MCP Governance Agent Identity"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    x_description = fields.Text()
    x_user_id = fields.Many2one(
        "res.users",
        string="Technical User",
        tracking=True,
        help="The Odoo user this agent operates as. ACLs and record rules "
        "of that user apply to every call the agent makes. Inbound HTTP "
        "requests made by this user appear under 'API Calls'.",
    )
    x_provider = fields.Selection(
        selection=[
            ("anthropic", "Anthropic (Claude)"),
            ("openai", "OpenAI"),
            ("google", "Google (Gemini)"),
            ("mistral", "Mistral"),
            ("other", "Other"),
        ],
        default="anthropic",
        required=True,
        tracking=True,
        string="Provider",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("revoked", "Revoked"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    x_owner_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        string="Owner",
        help="Business owner responsible for this agent (accountable party).",
    )
    active = fields.Boolean(default=True)

    x_api_call_count = fields.Integer(
        compute="_compute_api_call_count",
        string="API Calls",
    )

    _name_uniq = models.Constraint(
        "UNIQUE(name)",
        "An agent identity with this name already exists.",
    )

    @api.depends("x_user_id")
    def _compute_api_call_count(self):
        HttpRequest = self.env["auditlog.http.request"]
        for rec in self:
            rec.x_api_call_count = (
                HttpRequest.search_count([("user_id", "=", rec.x_user_id.id)])
                if rec.x_user_id
                else 0
            )

    def action_view_api_calls(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("API Calls — %s", self.name),
            "res_model": "auditlog.http.request",
            "view_mode": "list,form",
            "domain": [("user_id", "=", self.x_user_id.id)],
        }

    def action_activate(self):
        self.write({"state": "active"})

    def action_suspend(self):
        self.write({"state": "suspended"})

    def action_revoke(self):
        self.write({"state": "revoked", "active": False})
