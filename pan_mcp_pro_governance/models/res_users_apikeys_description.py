"""Wizard inherit: add an optional Role field when creating a new API key.

If the user picks a role, the generated key is bound to it and only sees
the role's groups during requests. If the user leaves it empty, the key
behaves like a standard Odoo API key — full user permissions.

This mirrors OCA `base_user_role`'s own posture: a user with no roles
keeps their groups untouched. Per ADR-010 (revised 2026-05-19).
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResUsersApikeysDescription(models.TransientModel):
    _inherit = "res.users.apikeys.description"

    x_role_id = fields.Many2one(
        comodel_name="res.users.role",
        string="Role",
        required=False,
        ondelete="restrict",
        help="Optional. If set, the key only sees this role's groups during "
             "requests. If empty, the key inherits the user's full permissions "
             "— the standard Odoo behaviour.",
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
        # If a role is chosen, validate it belongs to the current user.
        role_id = False
        if self.x_role_id:
            user_role_ids = self.env.user.sudo().role_line_ids.mapped("role_id").ids
            if self.x_role_id.id not in user_role_ids:
                raise UserError(_(
                    "Role %s is not assigned to your user. Ask an administrator "
                    "to assign it first.", self.x_role_id.display_name,
                ))
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
            vals = {"x_state": "active"}
            if role_id:
                vals["x_role_id"] = role_id
            new_key.write(vals)

        return action
