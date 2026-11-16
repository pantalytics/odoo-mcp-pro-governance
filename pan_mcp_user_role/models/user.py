# Copyright 2014 ABF OSIELL <http://osiell.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import api, fields, models

from .. import compat


class ResUsers(models.Model):
    _inherit = "res.users"

    role_line_ids = fields.One2many(
        comodel_name="res.users.role.line",
        inverse_name="user_id",
        string="Role lines",
        # A line's `active` is related to its user's, which an unsaved line
        # reads as False; with the default active_test the form would drop
        # it and `show_alert` would only flip after Save.
        context={"active_test": False},
        default=lambda self: self._default_role_lines(),
        groups="base.group_erp_manager",
    )

    show_alert = fields.Boolean(compute="_compute_show_alert")

    @api.depends("role_line_ids", "role_line_ids.date_from", "role_line_ids.date_to")
    def _compute_show_alert(self):
        for user in self:
            user.show_alert = user.role_line_ids.filtered(lambda rec: rec.is_enabled)

    # Not `role_ids`: Odoo's `mail` defines res.users.role_ids (mention
    # roles, `res.role`) and, loading after this module, replaces ours.
    x_role_ids = fields.Many2many(
        comodel_name="res.users.role",
        string="Access role",
        help="The access roles linked to this user (Access Rights tab).",
        compute="_compute_role_ids",
        compute_sudo=True,
        groups="base.group_erp_manager",
    )

    @api.model
    def _default_role_lines(self):
        """Default role lines for a new user.

        In Odoo 19, the former ``base.default_user`` template was removed in
        favor of a default group. There is no default user anymore to copy
        role lines from. Use a boolean on roles to mark the ones that should
        apply to new users.
        """
        default_roles = self.env["res.users.role"].search([("is_default", "=", True)])
        return [{"role_id": r.id} for r in default_roles]

    @api.depends("role_line_ids.role_id")
    def _compute_role_ids(self):
        for user in self:
            user.x_role_ids = user.role_line_ids.mapped("role_id")

    @api.model_create_multi
    def create(self, vals_list):
        new_records = super().create(vals_list)
        new_records.set_groups_from_roles()
        return new_records

    def write(self, vals):
        res = super().write(vals)
        self.sudo().set_groups_from_roles()
        return res

    def _get_enabled_roles(self):
        return self.role_line_ids.filtered(lambda rec: rec.is_enabled)

    def set_groups_from_roles(self, force=False):
        """Set (replace) the groups following the roles defined on users.

        If no role is defined on the user, its groups are left untouched.
        This holds under `force` as well: "no roles" always means "leave the
        groups alone" (see the guard in the loop below).

        The `force` parameter is kept for API compatibility -- callers such as
        `res.users.role.unlink()` and `res.users.role.line.unlink()` still pass
        `force=True` -- but it no longer bypasses that guard. Users that do
        carry role lines are recomputed either way, so a role edit still
        propagates to its users exactly as before.
        """
        role_groups = {}
        # We obtain all the groups associated to each role first, so that
        # it is faster to compare later with each user's groups.
        for role in self.mapped("role_line_ids.role_id"):
            # Transitive implied groups provided by the ORM
            # (all_implied_ids on 19, trans_implied_ids on <= 18).
            role_groups[role] = list(set(compat.implied_groups(role).ids))
        multi_company = self.env.ref("base.group_multi_company", raise_if_not_found=False)
        for user in self:
            # A user without role lines is not managed by this module, so its
            # groups are none of our business -- not even under `force`.
            # Without this, `role_line_ids.unlink()` (which calls
            # `set_groups_from_roles(force=True)`) computes an empty group set
            # for the now role-less user and strips *every* group off it,
            # turning an internal user into a share user. See issue #27.
            # Users that still have role lines fall through and are recomputed
            # as before, which is what `force` was there for.
            if not user.role_line_ids:
                continue
            user_group_ids = compat.user_groups(user).ids
            group_ids = []
            for role_line in user._get_enabled_roles():
                role = role_line.role_id
                group_ids += role_groups[role]
            group_ids = set(group_ids)
            # Administrator (base.group_system) is a choice per user, made
            # with the Role radio on the user form, not a role's (#60). The
            # sync never adds or removes it. A user who has it keeps it and
            # everything it implies, so no role edit or cron run can lock an
            # administrator out, and ticking Administrator on a user with a
            # role is no longer undone by the same save.
            admin_group = self.env.ref("base.group_system", raise_if_not_found=False)
            if admin_group and admin_group.id in user_group_ids:
                group_ids |= {admin_group.id, *compat.implied_groups(admin_group).ids}
            groups_to_add = group_ids - set(user_group_ids)
            groups_to_remove = set(user_group_ids) - group_ids
            if admin_group:
                groups_to_add.discard(admin_group.id)
                groups_to_remove.discard(admin_group.id)
            # base.group_multi_company follows the user's companies, not a
            # role: core links it when a user has more than one company and
            # unlinks it at one (res.users.write). Replacing the groups with
            # the role's closure used to undo that right after core did it,
            # hiding the company field on every record (#57). The sync applies
            # core's rule instead, so the 3-hourly cron also repairs users who
            # lost the group before this fix.
            if multi_company:
                groups_to_add.discard(multi_company.id)
                groups_to_remove.discard(multi_company.id)
                wanted = len(user.sudo().company_ids) > 1
                if wanted and multi_company.id not in user_group_ids:
                    groups_to_add.add(multi_company.id)
                elif not wanted and multi_company.id in user_group_ids:
                    groups_to_remove.add(multi_company.id)
            to_add = [fields.Command.link(gr) for gr in groups_to_add]
            to_remove = [fields.Command.unlink(gr) for gr in groups_to_remove]
            groups = to_remove + to_add
            if groups:
                vals = {compat.USER_GROUPS_FIELD: groups}
                super(ResUsers, user).write(vals)
        return True
