from odoo import models


class GetStarted(models.TransientModel):
    """Empty container model that backs the "Get Started" landing page.

    The page is purely static HTML rendered inside a form view; the model
    itself stores no data. We use a TransientModel so Odoo auto-creates a
    throwaway record when the action opens, which lets the form view render
    without an explicit res_id.
    """

    _name = "mcp.governance.get_started"
    _description = "MCP Pro Get Started landing"

    def _compute_display_name(self):
        # Without this, the breadcrumb on a brand-new transient record
        # shows the raw "model_name,NewId_0x..." debug string.
        for rec in self:
            rec.display_name = "Get Started"
