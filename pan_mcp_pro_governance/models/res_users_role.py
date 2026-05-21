"""Last-admin guard for role management.

If every user who can edit roles loses that ability in a single
transaction, the database becomes unrecoverable: nobody can fix the
roles, including the person who just broke them. Odoo itself ships
without this guard (see odoo/odoo#228513) and OCA base_user_role does
not add one either.

The guard is a NIST RBAC minimum-cardinality constraint (ANSI INCITS
359): at least one active internal user must hold the group that
authorises editing res.users.role — which in our ACL is
``base.group_erp_manager`` ("Administration: Settings").

Hook points:
- ``res.users.write`` — covers direct group assignment, archive, and
  the recompute fired by OCA when role_line_ids changes.
- ``res.users.role`` write/unlink — covers role-level edits (changing
  the role's implied groups, deleting a role outright) where the user
  recompute might not fire the constraint in time.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

ROLE_MANAGER_XMLID = "base.group_erp_manager"


def _has_role_managers(env):
    """At least one active internal user with role-management rights."""
    group = env.ref(ROLE_MANAGER_XMLID, raise_if_not_found=False)
    if not group:
        return True
    return bool(
        env["res.users"]
        .sudo()
        .search_count([("active", "=", True), ("group_ids", "in", group.id)], limit=1)
    )


_LOCKOUT_MESSAGE = (
    "This change would leave no user able to manage roles. "
    "Grant another active user the 'Administration: Settings' "
    "right (or include it in their role) before applying this change."
)


def _raise_lockout():
    # Plain string, not `_(...)`: the translate alias crashes when raised
    # outside a request context (e.g. set_groups_from_roles fired during
    # role-line write in TransactionCase). The English message is the only
    # one this module ships anyway.
    raise ValidationError(_LOCKOUT_MESSAGE)


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.constrains("group_ids", "active")
    def _check_minimum_role_manager(self):
        # Skip during module install/upgrade and before the registry is
        # ready: at those moments groups are still being assigned in
        # transient states (e.g. admin temporarily without a group while
        # rows are being moved by a security CSV reload), and the
        # constraint would fire spuriously. The check still runs for
        # every real, user-driven write afterwards.
        if self.env.context.get("install_mode") or not self.pool.ready:
            return
        if not _has_role_managers(self.env):
            _raise_lockout()


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

    def _compute_view_group_hierarchy(self):
        hierarchy = self.env["res.groups"]._get_view_group_hierarchy()
        for record in self:
            record.view_group_hierarchy = hierarchy

    def write(self, vals):
        result = super().write(vals)
        if not _has_role_managers(self.env):
            _raise_lockout()
        return result

    def unlink(self):
        result = super().unlink()
        if not _has_role_managers(self.env):
            _raise_lockout()
        return result
