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

from .. import compat


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    # The ``res_user_group_ids`` access-rights widget and
    # ``_get_view_group_hierarchy`` are new in Odoo 19. On 18 the role form
    # falls back to the OCA default (flat many2many_tags), so this field and
    # its compute are only declared on >= 19. See compat.py and the
    # version-gated role view.
    if compat.ODOO_VERSION >= 19:
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

        def _compute_view_group_hierarchy(self):
            hierarchy = self.env["res.groups"]._get_view_group_hierarchy()
            for record in self:
                record.view_group_hierarchy = hierarchy

    # Progressive-disclosure helper on the new-role form: pick a user
    # and the role's implied groups are seeded from theirs. Non-stored,
    # only meaningful at creation time; the view hides it once the role
    # is saved.
    x_copy_from_user_id = fields.Many2one(
        "res.users",
        string="Copy permissions from",
        store=False,
    )

    @api.onchange("x_copy_from_user_id")
    def _onchange_x_copy_from_user_id(self):
        for role in self:
            if role.x_copy_from_user_id:
                source_groups = compat.user_groups(role.x_copy_from_user_id)
                role.implied_ids = [fields.Command.set(source_groups.ids)]

    def _mcp_excess_group_ids(self, user):
        """Return the group ids this role implies that ``user`` does not have.

        The core API-key security invariant: a key can never grant more than
        its owner. An empty result means the role is a subset of the user's
        groups (eligible to bind a key). Single source of truth for the
        wizard's role filter, the key constraint, and ``make_key``.
        """
        self.ensure_one()
        role_group_ids = set(compat.implied_groups(self).ids)
        user_group_ids = set(compat.user_groups(user.sudo()).ids)
        return role_group_ids - user_group_ids
