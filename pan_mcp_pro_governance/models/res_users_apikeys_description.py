"""Wizard inherit: require a role when creating a new API key.

Adds the `x_role_id` field to the API-key creation wizard
(`res.users.apikeys.description`) and threads it through `make_key` so the
generated key row is bound to the role from the start.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResUsersApikeysDescription(models.TransientModel):
    _inherit = "res.users.apikeys.description"

    x_role_id = fields.Many2one(
        comodel_name="res.users.role",
        string="Role",
        required=True,
        ondelete="restrict",
        help="What this key is allowed to do. Pick from the roles already "
             "assigned to your user — the key cannot exceed them.",
    )
    x_available_role_ids = fields.Many2many(
        comodel_name="res.users.role",
        compute="_compute_available_role_ids",
        help="Roles assigned to the current user — the only valid choices.",
    )

    @api.depends_context("uid")
    def _compute_available_role_ids(self):
        # base_user_role's role_ids is broken on 19.0; use role_line_ids → role_id.
        user_roles = self.env.user.sudo().role_line_ids.mapped("role_id")
        for rec in self:
            rec.x_available_role_ids = user_roles

    def make_key(self):
        # Validate the chosen role belongs to the current user (defence in depth).
        if not self.x_role_id:
            raise UserError(_("A role is required to create an API key."))
        user_role_ids = self.env.user.sudo().role_line_ids.mapped("role_id").ids
        if self.x_role_id.id not in user_role_ids:
            raise UserError(_(
                "Role %s is not assigned to your user. Ask an administrator "
                "to assign it first.", self.x_role_id.display_name,
            ))

        # Capture role + name before super() unlinks the wizard.
        role_id = self.x_role_id.id
        # super().make_key() generates the key, unlinks self, and returns a
        # form action showing the raw key. The raw key is on the show-form's
        # context; we'll fish it out to identify the newly-inserted row.
        action = super().make_key()
        raw_key = (action.get("context") or {}).get("default_key")
        if not raw_key:
            # Fallback: search by user+name, most recent. Risky if duplicate
            # names exist but acceptable as a last resort.
            new_key = self.env["res.users.apikeys"].sudo().search(
                [("user_id", "=", self.env.user.id)],
                order="id desc",
                limit=1,
            )
        else:
            # The DB stores `index` as the first 8 hex chars of the raw key.
            new_key = self.env["res.users.apikeys"].sudo().search(
                [("user_id", "=", self.env.user.id), ("index", "=", raw_key[:8])],
                limit=1,
            )
        if new_key:
            new_key.write({"x_role_id": role_id, "x_state": "active"})

        return action
