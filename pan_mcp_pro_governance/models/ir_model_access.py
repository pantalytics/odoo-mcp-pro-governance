"""Narrow `ir.model.access` ACL checks to the API key's role.

When a request authenticates via an API key bound to a role, the question
"is this user allowed to read/write/create/unlink model X?" is answered
using **the role's groups**, not the full set of groups the underlying user
has. The DB user record is untouched.

This complements the `_has_group` override in `res_users.py`. Together they
cover the two main paths through Odoo's permission machinery:
- has_group() — used for menus, view-level groups, button gates
- ir.model.access.check() — used for ORM-level CRUD on models

Record rules (`ir.rule`) are a separate axis and are addressed in a
follow-up.
"""

import logging

from odoo import _, api, models
from odoo.exceptions import AccessError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    def check(self, model, mode="read", raise_exception=True):
        if self.env.su:
            return True

        role = self.env.user._get_api_key_role()
        if not role:
            return super().check(model, mode, raise_exception)

        # Defensive: validate mode like the parent does.
        assert mode in ("read", "write", "create", "unlink"), (
            f"Invalid access mode {mode!r}"
        )
        assert isinstance(model, str), f"Not a model name: {model}"

        allowed_group_ids = self._mcp_role_group_ids(role)
        if not allowed_group_ids:
            allowed_group_ids = (None,)  # makes IN-clause valid; no rows will match

        self.flush_model()
        self.env.cr.execute(
            SQL(
                """
                SELECT 1
                  FROM ir_model_access a
                  JOIN ir_model m ON m.id = a.model_id
                 WHERE a.perm_%s
                   AND a.active
                   AND m.model = %s
                   AND (a.group_id IS NULL OR a.group_id IN %s)
                 LIMIT 1
                """,
                SQL(mode),
                model,
                tuple(allowed_group_ids),
            )
        )
        has_access = bool(self.env.cr.fetchone())

        if not has_access:
            _logger.info(
                "MCP Pro Governance: ACL denied for role=%s mode=%s model=%s "
                "(user=%s, request authenticated via role-bound API key)",
                role.display_name, mode, model, self.env.user.login,
            )
            if raise_exception:
                raise self._make_access_error(model, mode)
        return has_access

    def _make_access_error(self, model: str, mode: str):
        """Override the standard access-error message when a role-bound API
        key authenticated the request. The default message says "you need
        group X" which is misleading — the actual fix is to broaden the role
        or pick a different one when creating the key.
        """
        role = self.env.user._get_api_key_role() if hasattr(self.env.user, "_get_api_key_role") else None
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
                "Settings → Users & Companies → User Roles, or use an API key "
                "bound to a broader role.",
                role=role.display_name, operation=op_label, model=model,
            )
        )

    @staticmethod
    def _mcp_role_group_ids(role):
        """Return the set of res.groups ids effective for this role.

        Includes the role's own primary group, the groups it explicitly
        implies, and groups transitively implied by those.
        """
        groups = role.group_id | role.implied_ids
        # `all_implied_ids` is the transitive closure on res.groups; fall back to
        # implied_ids if some Odoo branch hasn't shipped it.
        if "all_implied_ids" in groups._fields:
            groups |= groups.mapped("all_implied_ids")
        else:
            groups |= groups.mapped("implied_ids")
        return groups.ids
