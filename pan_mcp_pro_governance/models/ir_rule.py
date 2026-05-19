"""Make ``ir.rule._compute_domain`` cache-aware of the API-key role.

Parent caches on (uid, su, model_name, mode, _compute_domain_context_values()).
Without role-awareness, the first call for a uid would cache its domain
for all subsequent role contexts.

Cleanest fix: extend ``_compute_domain_keys`` to include our role-id
context key. The parent threads that key into the cache tuple. Then we
just need to ensure the key is populated in env.context during a
role-bound API-key request — done via ``_compute_domain`` here.

Effect: each (uid, role_id) pair gets its own cache entry. Within a
role-bound request, the parent's domain computation reads ``user
._get_group_ids()`` and ``user.all_group_ids``, both narrowed via the
overrides in ``res_users.py``.
"""

from odoo import api, models

_MCP_ROLE_CTX_KEY = "_mcp_api_key_role_id"


class IrRule(models.Model):
    _inherit = "ir.rule"

    def _compute_domain_keys(self):
        # Include our key so the cache differentiates per role.
        return super()._compute_domain_keys() + [_MCP_ROLE_CTX_KEY]

    @api.model
    def _compute_domain(self, model_name, mode="read"):
        role = self.env.user._get_api_key_role() if hasattr(self.env.user, "_get_api_key_role") else None
        if not role:
            return super()._compute_domain(model_name, mode)
        # Thread the role id through the env context so the cache key
        # captures it; parent then computes correctly via narrowed group reads.
        return super(IrRule, self.with_context(
            **{_MCP_ROLE_CTX_KEY: role.id}
        ))._compute_domain(model_name, mode)
