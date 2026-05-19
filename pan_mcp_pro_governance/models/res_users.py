"""Narrow user's effective groups when an API key with a role authenticates.

When a request authenticates via an API-key bound to a role, *every*
Odoo permission path that ultimately asks "what groups does this user
have?" gets the role's groups, not the user's actual groups. The user
record in the database is unchanged.

This is implemented in two places that together cover all of Odoo's
permission machinery:

- ``_get_group_ids()`` — returns a tuple of group ids. Parent is
  ``@tools.ormcache('self.id')``-cached, so we override here to bypass
  the cache (and return the role's groups) when an API-key role is in
  scope. Consumers: ``_has_group``, ``ir.model.access._get_allowed_models``,
  ``ir.rule._get_rules``.

- ``_compute_all_group_ids`` — assigns the ``all_group_ids`` M2M field
  on ``res.users``. Used by ``ir.rule._compute_domain`` for the
  rule-group intersection filter. Without this override, record rules
  would still be evaluated against the user's full groups.

Both narrowing paths consult ``_get_api_key_role()``, which reads from
``request.session`` first (modern bearer auth, request on stack) and
falls back to a thread-local (legacy ``/jsonrpc`` path where the
request is popped during dispatch). UI sessions are unaffected because
``_get_api_key_role`` returns False when no API-key context is active.
"""

from odoo import api, models
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _get_api_key_role(self):
        """Return the active API-key role for this request, or False."""
        from .res_users_apikeys import get_thread_api_key_role_id

        role_id = None
        if request:
            role_id = request.session.get("x_mcp_api_key_role_id")
        if not role_id:
            role_id = get_thread_api_key_role_id()
        if not role_id:
            return False
        role = self.env["res.users.role"].sudo().browse(role_id)
        if not role.exists():
            return False
        return role

    def _mcp_role_group_ids(self, role):
        """Transitive closure of res.groups for a role."""
        groups = role.group_id | role.implied_ids
        if "all_implied_ids" in groups._fields:
            groups |= groups.mapped("all_implied_ids")
        else:
            groups |= groups.mapped("implied_ids")
        return groups

    def _get_group_ids(self):
        """Override: return role's groups (bypassing parent's ormcache)
        when this user is the active env user and an API-key role is set.

        Returning a fresh tuple from this method skips the parent's
        ``@tools.ormcache('self.id')`` because the cache lookup happens
        inside the parent implementation; we never call it for the
        narrowed case.
        """
        if self == self.env.user:
            role = self._get_api_key_role()
            if role:
                return tuple(self._mcp_role_group_ids(role).ids)
        return super()._get_group_ids()

    @api.depends("group_ids.all_implied_ids")
    def _compute_all_group_ids(self):
        """Override: narrow ``all_group_ids`` to the role's groups for
        the current env user when an API-key role is set. This is what
        ``ir.rule._compute_domain`` reads when filtering rules by group
        intersection.

        For other users in the recordset (e.g. admin inspecting another
        user) the parent computation applies.
        """
        active_role = self._get_api_key_role()
        env_user = self.env.user
        for user in self:
            if active_role and user == env_user:
                user.all_group_ids = self._mcp_role_group_ids(active_role)
            else:
                user.all_group_ids = user.group_ids.all_implied_ids
