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

import contextlib
import string

from odoo import api, models, tools
from odoo.http import request

from .. import compat
from .ir_http import set_audit_api_key_id


def _mcp_looks_like_api_key(passwd):
    """True when `passwd` has the shape of an Odoo API key.

    Keys are `API_KEY_SIZE` random bytes rendered as hex. Checking the
    shape first means a normal password login never pays for the extra
    cursor in the Odoo 17 `check()` override.
    """
    if not passwd:
        return False
    from odoo.addons.base.models.res_users import API_KEY_SIZE

    return len(passwd) == API_KEY_SIZE * 2 and all(c in string.hexdigits for c in passwd)


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    @tools.ormcache("uid", "passwd")
    def _mcp_resolve_api_key(self, uid, passwd):
        """Return ``(api_key_id, role_id)`` for an active key matching
        ``(uid, passwd)``, or ``(False, False)``.

        Cached on the same key as Odoo's own ``_check_uid_passwd``
        ormcache so it invalidates together with password/key changes.
        We need our own lookup because the parent cache hides the
        ``_check_credentials`` chain on cache hits — which would
        otherwise be the only place we learn the API key id and role.
        """
        if not passwd or not uid:
            return (False, False)
        from odoo.addons.base.models.res_users import (
            INDEX_SIZE,
            KEY_CRYPT_CONTEXT,
        )

        index = passwd[:INDEX_SIZE]
        self.env.cr.execute(
            "SELECT id, key, x_role_id, x_state "
            "FROM res_users_apikeys "
            "WHERE user_id = %s AND index = %s",
            (uid, index),
        )
        for kid, hashed, role_id, state in self.env.cr.fetchall():
            if KEY_CRYPT_CONTEXT.verify(passwd, hashed):
                if state != "active":
                    return (False, False)
                return (kid, role_id or False)
        return (False, False)

    @api.model
    def _check_uid_passwd(self, uid, passwd):
        """Override: always seed the audit snapshot AND the role
        thread-local for the resolved API key. Parent is
        ``ormcache('uid', 'passwd')`` so on cache hits the
        ``_check_credentials`` chain — the only place narrowing is
        normally wired up — is skipped. Without this override a
        role-bound key only narrows on its first call per worker.
        """
        result = super()._check_uid_passwd(uid, passwd)
        api_key_id, role_id = self.sudo()._mcp_resolve_api_key(uid, passwd)
        if api_key_id:
            set_audit_api_key_id(api_key_id)
        if role_id:
            from .res_users_apikeys import set_thread_api_key_role_id

            set_thread_api_key_role_id(role_id)
        return result

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
        groups |= groups.mapped(compat.IMPLIED_FIELD)
        return groups

    def _get_group_ids(self):
        """Override: return role's groups (bypassing parent's ormcache)
        when this user is the active env user and an API-key role is set.

        Returning a fresh tuple from this method skips the parent's
        ``@tools.ormcache('self.id')`` because the cache lookup happens
        inside the parent implementation; we never call it for the
        narrowed case.

        On Odoo 17 there is no parent implementation at all (the method
        arrived in 18), so the un-narrowed branch falls back to a plain
        read of the user's groups. Our own overrides call this method on
        every version, so it has to answer on 17 too.
        """
        if self == self.env.user:
            role = self._get_api_key_role()
            if role:
                return tuple(self._mcp_role_group_ids(role).ids)
        if compat.ODOO_VERSION < 18:
            return tuple(compat.user_groups(self)._ids)
        return super()._get_group_ids()

    # ``all_group_ids`` and its compute are new in Odoo 19. On 18 the field
    # does not exist, so this override is omitted there — narrowing on 18
    # rides entirely on ``_get_group_ids`` plus the ir.model.access /
    # ir.rule overrides, which both read it. See compat.py.
    if compat.ODOO_VERSION >= 19:

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

    # ------------------------------------------------------------------
    # Odoo 17 only — 17 has no group-resolution seam
    # ------------------------------------------------------------------
    # From Odoo 18 on, `ir.model.access._get_allowed_models`,
    # `ir.rule._get_rules` and `res.users._has_group` all resolve groups
    # through `_get_group_ids()`, so overriding that one method narrows
    # every permission path. Odoo 17 has no such method: each of those
    # call sites runs its own SQL against `res_groups_users_rel` keyed on
    # `uid`. Without the overrides below, a role-bound API key on 17 is
    # authenticated but never narrowed — the key keeps the owner's full
    # rights. See docs/dev/odoo-17-narrowing.md.
    if compat.ODOO_VERSION < 18:

        @api.model
        def _has_group(self, group_ext_id):
            """Answer group checks from the role's groups when one is active.

            Core's 17 implementation is `@ormcache('self._uid', ...)`; we
            return before calling it so the cache is never consulted for a
            narrowed request, exactly as `_get_group_ids` does.

            Like core, the subject is `self.env.user` — a `with_user()`
            check inside a narrowed request therefore answers for the role,
            not for that other user. Same shape as the `_get_group_ids`
            override on 18/19.
            """
            role = self._get_api_key_role()
            if not role:
                return super()._has_group(group_ext_id)
            group_id = self.env["ir.model.data"]._xmlid_to_res_id(
                group_ext_id, raise_if_not_found=False
            )
            return bool(group_id) and group_id in self.env.user._get_group_ids()

        @classmethod
        def check(cls, db, uid, passwd):
            """Odoo 17 equivalent of the `_check_uid_passwd` override.

            17 authenticates RPC through this classmethod, which is
            `@ormcache('uid', 'passwd')`. On a cache hit the
            `_check_credentials` chain — where the role and the audit
            api-key id are normally wired up — is skipped, so a role-bound
            key narrowed only on its first call per worker. That is what
            made the behaviour on the customer's staging intermittent.

            Re-resolve on every call, from our own ormcached resolver so a
            hit costs no SQL. The cursor is only opened for credentials
            shaped like an API key, which keeps ordinary password logins
            on exactly the path they had before.
            """
            result = super().check(db, uid, passwd)
            if not _mcp_looks_like_api_key(passwd):
                return result
            with contextlib.closing(cls.pool.cursor()) as cr:
                env = api.Environment(cr, api.SUPERUSER_ID, {})
                api_key_id, role_id = env["res.users"]._mcp_resolve_api_key(uid, passwd)
            if api_key_id:
                set_audit_api_key_id(api_key_id)
            if role_id:
                from .res_users_apikeys import set_thread_api_key_role_id

                set_thread_api_key_role_id(role_id)
            return result
