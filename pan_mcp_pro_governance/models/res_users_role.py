"""Role-form UX helpers.

Odoo core's ``_check_at_least_one_administrator`` already guarantees at
least one active user holds ``base.group_system``, which implies
``base.group_erp_manager`` — the right to manage roles. A separate
lockout guard at this layer would be redundant and produced false
positives (toggling unrelated fields on a role tripped it because the
admin's group_erp_manager came from implication, not direct
assignment, and the guard searched ``group_ids`` instead of
``all_group_ids``).
"""

from odoo import api, fields, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    # On a *new* role record the inherited `view_group_hierarchy`
    # compute on res.groups does not run (no associated group_id
    # exists until save). The standard `res_user_group_ids` widget
    # then crashes on `Object.values(undefined)`. Redeclare the field
    # locally with a compute that always returns the global hierarchy,
    # which is correct for both new and existing roles since the
    # hierarchy is identical for every record.
    view_group_hierarchy = fields.Json(
        compute="_compute_view_group_hierarchy",
        store=False,
        copy=False,
    )

    # Progressive-disclosure helper on the new-role form: pick a user
    # and the role's implied groups are seeded from theirs. Non-stored,
    # only meaningful at creation time; the view hides it once the role
    # is saved.
    x_copy_from_user_id = fields.Many2one(
        "res.users",
        string="Copy permissions from",
        store=False,
    )

    def _compute_view_group_hierarchy(self):
        hierarchy = self.env["res.groups"]._get_view_group_hierarchy()
        for record in self:
            record.view_group_hierarchy = hierarchy

    @api.onchange("x_copy_from_user_id")
    def _onchange_x_copy_from_user_id(self):
        for role in self:
            if role.x_copy_from_user_id:
                role.implied_ids = [fields.Command.set(role.x_copy_from_user_id.group_ids.ids)]
