"""Wizard inherit: add an optional Role field when creating a new API key.

If the user picks a role, the generated key is bound to it and only sees
the role's groups during requests. If the user leaves it empty, the key
behaves like a standard Odoo API key — full user permissions.

The valid roles are those whose implied groups are a subset of the
current user's groups. This is the real security invariant: a key
cannot grant more than its owner. We deliberately do **not** require
the role to be *assigned* to the user via OCA `role_line_ids` — doing
so would trigger OCA's enforcement that resets the user's groups to
only what the role implies, stripping the user of unrelated UI
permissions (Audit Log menu, Activities, Studio, etc.). The whole
point of this addon is to scope AI keys without forcing operators to
create extra internal users (per ADR-005 / Odoo billing constraints).
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
        help="Roles whose groups are a subset of your own — the only valid "
        "choices, since a key cannot grant more than its owner.",
    )

    # `name` is a real, always-set field on the wizard; depending on it forces
    # the compute to actually run on Odoo 18. With only @api.depends_context
    # and no field dependency, Odoo 18 never schedules the compute, so the
    # field stays at its empty default (Odoo 19 computes it lazily on read).
    @api.depends("name")
    @api.depends_context("uid")
    def _compute_available_role_ids(self):
        user = self.env.user
        all_roles = self.env["res.users.role"].sudo().search([])
        eligible = all_roles.filtered(lambda r: not r._mcp_excess_group_ids(user))
        for rec in self:
            rec.x_available_role_ids = eligible

    def make_key(self):
        # If a role is chosen, validate its groups are a subset of the user's.
        role_id = False
        if self.x_role_id:
            excess = self.x_role_id._mcp_excess_group_ids(self.env.user)
            if excess:
                missing = self.env["res.groups"].browse(list(excess)).mapped("display_name")
                raise UserError(
                    _(
                        "Role '%(role)s' includes groups you do not have: %(missing)s. "
                        "A key cannot grant more than its owner. Ask an administrator "
                        "to either add the missing groups to your user, or pick a "
                        "narrower role.",
                        role=self.x_role_id.display_name,
                        missing=", ".join(missing),
                    )
                )
            role_id = self.x_role_id.id

        # super().make_key() generates exactly one key for this user and
        # unlinks the wizard. The newest key for this user is therefore the
        # one we just created.
        action = super().make_key()
        new_key = (
            self.env["res.users.apikeys"]
            .sudo()
            .search(
                [("user_id", "=", self.env.user.id)],
                order="id desc",
                limit=1,
            )
        )
        if new_key:
            vals = {"x_state": "active"}
            if role_id:
                vals["x_role_id"] = role_id
            new_key.write(vals)

        return action
