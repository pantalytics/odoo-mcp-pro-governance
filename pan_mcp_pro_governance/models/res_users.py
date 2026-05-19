"""Narrow effective groups when an API key with a role authenticates.

When `request.session['x_mcp_api_key_role_id']` is set, the user's
`_has_group()` answers as if the user only had that single role's groups,
not their full role bag. The user record in the DB is unchanged.

NOTE on scope (read this before building features on top):

This override narrows `has_group()` checks. That covers:
- Menu / submenu visibility (groups="..." on menuitems)
- View-level field/button visibility (groups="..." on view elements)
- Computed-field group gates
- Server-action / wizard access gates

It does NOT yet narrow:
- `ir.model.access` ACL checks at the ORM layer (search/read/write/create/unlink)
- `ir.rule` record-rule WHERE clauses

For a key+role to truly limit what the integration can do at the data layer,
the next iteration needs to override `ir.model.access.check()` and/or
`ir.rule._compute_domain()` to consult the session role. Tracking as open
question #1 in ADR-010.
"""

import logging

from odoo import api, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _get_api_key_role(self):
        """Return the active API-key role for this request, or False.

        Reads from two channels:
        - request.session (modern bearer auth path keeps the request on the
          local stack, session writes persist)
        - thread-local (legacy /jsonrpc path pops the request via
          borrow_request, so session writes don't survive; thread-local does)

        The first non-empty value wins.
        """
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

    def _has_group(self, group_ext_id: str) -> bool:
        role = self._get_api_key_role()
        if not role or self != self.env.user:
            # Either no API-key role on this request, or the caller is asking
            # about a different user (admin inspecting someone else) — do NOT
            # narrow that.
            return super()._has_group(group_ext_id)

        group_id = self.env["res.groups"]._get_group_definitions().get_id(group_ext_id)
        if not group_id:
            return False

        # Role's effective groups = the role's own group + everything it implies.
        # base_user_role stores the role's underlying `res.groups` on `group_id`,
        # and uses `implied_ids` for the role's chosen groups.
        allowed = role.group_id | role.implied_ids
        # Include transitively implied groups (groups implied by the implied groups).
        allowed |= allowed.mapped("all_implied_ids") if "all_implied_ids" in allowed._fields else allowed.mapped("implied_ids")
        return group_id in allowed.ids
