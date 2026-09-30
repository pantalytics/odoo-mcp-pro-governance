"""Odoo 20+: API-key role narrowing on the unified ``ir.access`` model.

Odoo 20 merged ``ir.model.access`` and ``ir.rule`` into ``ir.access``. Every
access check now goes through ``BaseModel._access_domain``, which reads the
user's groups from ``res.users._get_group_ids()`` (narrowed to the role in
``res_users.py``) and is ormcached on ``env._access_context``: the uid plus
whatever ``ir.access._get_access_context()`` yields. So on 20 three small
hooks replace ``ir_model_access.py`` and ``ir_rule.py``:

1. ``_get_access_context`` adds the role id to the cache key. Without it the
   first call for a uid would cache its domains for every later role context
   (same poisoning the 17-19 overrides guard against). The same key also
   splits the per-transaction read-access cache.
2. ``_make_model_access_error`` explains the refusal at the role layer
   instead of listing groups the owning user may well have.
3. ``ir.model._access_domain`` lets a scoped key read the model catalogue,
   limited to the models its role may read, so the MCP ``list_models`` tool
   mirrors the role. On 17-19 this is an ACL grant plus the global rule in
   ``security/mcp_scoped_model_list.xml``.
"""

from odoo import api, models
from odoo.fields import Domain

from .res_users import MCP_INTROSPECTION_MODELS


class IrAccess(models.Model):
    _inherit = "ir.access"

    def _get_access_context(self):
        yield from super()._get_access_context()
        yield self.env["res.users"]._mcp_api_key_role_id() or False

    @api.model
    def _mcp_readable_models(self):
        """Models the current (role-narrowed) user holds a read permission on.

        Equivalent of 17-19's ``_get_allowed_models("read")`` plus the
        introspection grant: permissions only (records with a group), domains
        ignored, exactly like the old ACL layer.
        """
        from odoo.addons.base.models.ir_access import IN_SELECTION

        group_ids = set(self.env.user._get_group_ids())
        readable = IN_SELECTION["read"]
        allowed = {
            model_name
            for model_name, accesses in self._get_all_access().items()
            if any(a.group_id in group_ids and a.operation in readable for a in accesses)
        }
        return frozenset(allowed) | frozenset(MCP_INTROSPECTION_MODELS)

    def _make_model_access_error(self, model_name, operation):
        role = self.env.user._get_api_key_role()
        if not role:
            return super()._make_model_access_error(model_name, operation)
        return self.env.user._mcp_role_access_error(role, model_name, operation)


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def _access_domain(self, operation):
        if operation != "read" or not self.env.user._get_api_key_role():
            return super()._access_domain(operation)
        return Domain(self.env.user._mcp_ir_model_domain())
