from odoo import fields, models


class McpGovernanceAgentIdentity(models.Model):
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
        "of that user apply to every call the agent makes.",
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
    x_last_seen = fields.Datetime(readonly=True, string="Last Seen")
    x_owner_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        string="Owner",
        help="Business owner responsible for this agent (accountable party).",
    )
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint(
        "UNIQUE(name)",
        "An agent identity with this name already exists.",
    )

    def action_activate(self):
        self.write({"state": "active"})

    def action_suspend(self):
        self.write({"state": "suspended"})

    def action_revoke(self):
        self.write({"state": "revoked", "active": False})
