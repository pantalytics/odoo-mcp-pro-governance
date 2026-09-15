"""Narrow ACL checks and rewrite the error message when an API-key role
is in scope.

Two pieces:

1. ``_get_allowed_models`` — parent is ``@tools.ormcache(self.env.uid, mode)``.
   The cache key has no role, so a single uid's first call would cache
   the answer for all subsequent role contexts. We override to bypass
   the cache and re-run the query with ``user._get_group_ids()`` (which
   is itself narrowed via the override in ``res_users.py``).

2. ``_make_access_error`` — Odoo's default message says "you need
   group X" which is misleading when the real fix is at the role
   layer. Override to surface the role-specific context. Odoo 17 has
   no such seam (it builds the message inline in ``check()``), so on
   17 the operator sees core's wording. Cosmetic only — the access
   decision itself is narrowed on every supported version.

We no longer override ``check()`` itself: parent's ``check`` reads from
``_get_allowed_models``, which we now narrow at the source.
"""

from odoo import _, models
from odoo.exceptions import AccessError


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    def _get_allowed_models(self, mode="read"):
        role = (
            self.env.user._get_api_key_role()
            if hasattr(self.env.user, "_get_api_key_role")
            else None
        )
        if not role:
            return super()._get_allowed_models(mode)

        # Live compute, bypassing the parent's ormcache (which is keyed
        # on uid only and would poison across role contexts). _get_group_ids
        # is itself role-narrowed via res_users.py.
        # `mode` is whitelisted right here, so interpolating it into the
        # statement is safe — core does the same. Plain `cr.execute` rather
        # than `env.execute_query`: the latter only exists from Odoo 18, and
        # calling it on 17 raised `AttributeError: 'Environment' object has
        # no attribute 'execute_query'` on every scoped request.
        assert mode in ("read", "write", "create", "unlink"), f"Invalid mode {mode!r}"
        group_ids = self.env.user._get_group_ids()
        self.flush_model()
        self.env.cr.execute(
            f"""
            SELECT m.model
              FROM ir_model_access a
              JOIN ir_model m ON (m.id = a.model_id)
             WHERE a.perm_{mode} AND a.active
               AND (a.group_id IS NULL OR a.group_id IN %s)
            GROUP BY m.model
            """,
            (tuple(group_ids) or (None,),),
        )
        return frozenset(v[0] for v in self.env.cr.fetchall())

    def _make_access_error(self, model: str, mode: str):
        role = None
        if hasattr(self.env.user, "_get_api_key_role"):
            role = self.env.user._get_api_key_role()
        if not role:
            return super()._make_access_error(model, mode)

        operation_labels = {
            "read": _("read"),
            "write": _("write"),
            "create": _("create"),
            "unlink": _("delete"),
        }
        op_label = operation_labels.get(mode, mode)
        return AccessError(
            _(
                "The API key you are using is bound to the role '%(role)s', "
                "which does not allow %(operation)s on model '%(model)s'.\n\n"
                "To fix: either add the required groups to this role in "
                "MCP Pro → Roles, or use an API key bound to a broader role.",
                role=role.display_name,
                operation=op_label,
                model=model,
            )
        )
