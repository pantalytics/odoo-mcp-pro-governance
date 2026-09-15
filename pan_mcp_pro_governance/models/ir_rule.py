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

Two version gaps need more than the cache key:

- ``_get_rules`` resolves groups via ``_get_group_ids()`` from Odoo 18
  on, but runs its own ``res_groups_users_rel`` SQL on 17. Overridden
  below for 17.
- ``_compute_domain`` intersects each rule's groups with the user's own
  groups. Odoo 19 reads ``all_group_ids`` (narrowed by the compute
  override in ``res_users.py``); 17 and 18 read ``groups_id`` directly,
  which no override reaches. Without the reimplementation below, record
  rules bound to the user's non-role groups are silently dropped from
  the domain, so a narrowed key sees *more* rows than its role allows.
"""

from odoo import api, models

from .. import compat

_MCP_ROLE_CTX_KEY = "_mcp_api_key_role_id"


class IrRule(models.Model):
    _inherit = "ir.rule"

    def _compute_domain_keys(self):
        # Include our key so the cache differentiates per role.
        return super()._compute_domain_keys() + [_MCP_ROLE_CTX_KEY]

    @api.model
    def _compute_domain(self, model_name, mode="read"):
        role = (
            self.env.user._get_api_key_role()
            if hasattr(self.env.user, "_get_api_key_role")
            else None
        )
        if not role:
            return super()._compute_domain(model_name, mode)
        # Thread the role id through the env context so the cache key
        # captures it; parent then computes correctly via narrowed group reads.
        this = self.with_context(**{_MCP_ROLE_CTX_KEY: role.id})
        if compat.ODOO_VERSION >= 19:
            return super(IrRule, this)._compute_domain(model_name, mode)
        return this._mcp_compute_domain_narrowed(model_name, mode, role)

    def _mcp_compute_domain_narrowed(self, model_name, mode, role):
        """Odoo 17/18 only: ``_compute_domain`` with the role's groups.

        Core on 17 and 18 reads ``self.env.user.groups_id`` for the
        rule/group intersection — a plain stored-field read with no seam
        to override. The body below mirrors core's (the 17.0 and 18.0
        implementations are byte-identical) with that one read swapped for
        the role's group closure. Revisit on any major upgrade; from 19 on
        this path is unused because core reads ``all_group_ids``.
        """
        from odoo.osv import expression
        from odoo.tools.safe_eval import safe_eval

        global_domains = []
        for parent_model_name, parent_field_name in self.env[model_name]._inherits.items():
            if domain := self._compute_domain(parent_model_name, mode):
                global_domains.append([(parent_field_name, "any", domain)])

        rules = self._get_rules(model_name, mode=mode)
        if not rules:
            return expression.AND(global_domains) if global_domains else []

        eval_context = self._eval_context()
        user_groups = self.env["res.users"]._mcp_role_group_ids(role)
        group_domains = []
        for rule in rules.sudo():
            dom = safe_eval(rule.domain_force, eval_context) if rule.domain_force else []
            dom = expression.normalize_domain(dom)
            if not rule.groups:
                global_domains.append(dom)
            elif rule.groups & user_groups:
                group_domains.append(dom)

        if not group_domains:
            return expression.AND(global_domains)
        return expression.AND(global_domains + [expression.OR(group_domains)])

    # Odoo 17 resolves the rules themselves straight from
    # `res_groups_users_rel`; 18+ go through `_get_group_ids()`, which is
    # already narrowed in `res_users.py`.
    if compat.ODOO_VERSION < 18:

        def _get_rules(self, model_name, mode="read"):
            role = (
                self.env.user._get_api_key_role()
                if hasattr(self.env.user, "_get_api_key_role")
                else None
            )
            if not role:
                return super()._get_rules(model_name, mode=mode)
            if mode not in self._MODES:
                raise ValueError(f"Invalid mode: {mode!r}")
            if self.env.su:
                return self.browse(())
            group_ids = tuple(self.env.user._get_group_ids()) or (None,)
            self.env.cr.execute(
                f"""
                SELECT r.id FROM ir_rule r
                JOIN ir_model m ON (r.model_id = m.id)
                WHERE m.model = %s AND r.active AND r.perm_{mode}
                  AND (r.global OR r.id IN (
                        SELECT rule_group_id FROM rule_group_rel rg
                        WHERE rg.group_id IN %s
                  ))
                ORDER BY r.id
                """,
                (model_name, group_ids),
            )
            return self.browse(row[0] for row in self.env.cr.fetchall())
