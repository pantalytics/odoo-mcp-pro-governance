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
   layer. Override to surface the role-specific context.

We no longer override ``check()`` itself: parent's ``check`` reads from
``_get_allowed_models``, which we now narrow at the source.
"""

from odoo import _, models
from odoo.exceptions import AccessError
from odoo.tools import SQL

# Models the MCP introspection tools (notably the server's ``list_models``
# tool, which does a ``search_read`` on ``ir.model``) must be able to read to
# enumerate the catalogue -- even for a scoped read-only role that holds none
# of the technical-model groups. We add these to the role's read set below so
# the ACL check passes; the *rows* of ``ir.model`` are then scoped back to the
# role's own models by the global rule in
# ``security/mcp_scoped_model_list.xml`` (see ``res.users._mcp_ir_model_domain``),
# so this never widens what a key can actually read.
MCP_INTROSPECTION_MODELS = ("ir.model",)


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
        assert mode in ("read", "write", "create", "unlink"), f"Invalid mode {mode!r}"
        group_ids = self.env.user._get_group_ids()
        self.flush_model()
        rows = self.env.execute_query(
            SQL(
                """
                SELECT m.model
                  FROM ir_model_access a
                  JOIN ir_model m ON (m.id = a.model_id)
                 WHERE a.perm_%s AND a.active
                   AND (a.group_id IS NULL OR a.group_id IN %s)
                GROUP BY m.model
                """,
                SQL(mode),
                tuple(group_ids) or (None,),
            )
        )
        allowed = frozenset(v[0] for v in rows)
        # Let a scoped key read the model catalogue itself so the MCP
        # ``list_models`` tool returns the role's models instead of an empty
        # list. Read-only: never inject for write/create/unlink.
        if mode == "read":
            allowed |= frozenset(MCP_INTROSPECTION_MODELS)
        return allowed

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
