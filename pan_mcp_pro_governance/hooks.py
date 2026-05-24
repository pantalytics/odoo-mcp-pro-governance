"""Install/uninstall hooks.

The `post_init_hook` seeds `auditlog.rule` records for the models AI agents
touch most often. Rules are created in draft state with no user filter, so
they have zero effect until the operator opens the rule, optionally
restricts it to the MCP technical user, and clicks "Subscribe".

Seeding is conditional: a rule is only created if the target model is
already installed in this database. This avoids forcing this addon to
depend on `sale`, `crm`, `account`, etc.
"""

import logging

_logger = logging.getLogger(__name__)


SEEDED_RULES = [
    ("sale.order", "MCP Pro — Sales Orders"),
    ("res.partner", "MCP Pro — Contacts"),
    ("account.move", "MCP Pro — Invoices & Bills"),
    ("crm.lead", "MCP Pro — CRM Leads & Opportunities"),
    ("product.template", "MCP Pro — Products"),
    ("stock.picking", "MCP Pro — Transfers"),
]


def ensure_admin_in_manager_group(env):
    """Add the built-in admin user to the MCP Pro Manager group.

    The reverse binding in security/mcp_pro_governance_groups.xml does not
    work on a fresh install (`user_ids` on res.groups silently fails to
    propagate), and the inverse XML — writing group_ids on base.user_admin
    — is rejected because that xmlid is marked noupdate. Doing it in Python
    bypasses both. Idempotent.
    """
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    manager_group = env.ref(
        "pan_mcp_pro_governance.group_mcp_governance_manager",
        raise_if_not_found=False,
    )
    if not admin or not manager_group:
        _logger.warning(
            "MCP Pro: could not add admin to Manager group (admin=%s, group=%s).",
            admin,
            manager_group,
        )
        return
    if manager_group in admin.group_ids:
        return
    env.cr.execute(
        "INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (manager_group.id, admin.id),
    )
    env.invalidate_all()
    _logger.info("MCP Pro: added %s to %s.", admin.login, manager_group.name)


def ensure_default_admin_role(env):
    """Seed a default "Administrator" role on first install.

    `pan_mcp_user_role` ships with zero roles. With no role records,
    operators cannot bind an API key to a role — and the role dropdown
    on the key-creation wizard is empty, which looks broken. Worse, an
    operator who has only role-bound keys configured elsewhere could
    lock themselves out before they realise they need to define roles.

    Seed one role that mirrors the built-in administrator: it implies
    `base.group_system`, which itself implies every other privilege.
    The operator can edit it, add more roles, or unlink it freely.
    Idempotent — re-running does nothing.
    """
    Role = env["res.users.role"]
    if Role.search_count([], limit=1):
        return
    group_system = env.ref("base.group_system", raise_if_not_found=False)
    if not group_system:
        _logger.warning("MCP Pro: base.group_system missing, skipping default role seed.")
        return
    Role.create(
        {
            "name": "Administrator",
            "implied_ids": [(6, 0, [group_system.id])],
        }
    )
    _logger.info("MCP Pro: seeded default 'Administrator' role.")


def post_init_hook(env):
    """Seed auditlog rules, default role, and grant admin Manager access."""
    ensure_admin_in_manager_group(env)
    ensure_default_admin_role(env)
    IrModel = env["ir.model"]
    AuditlogRule = env["auditlog.rule"]

    for model_name, rule_name in SEEDED_RULES:
        model = IrModel.search([("model", "=", model_name)], limit=1)
        if not model:
            _logger.info(
                "MCP Pro: skipping auditlog rule for %s (model not installed).",
                model_name,
            )
            continue
        if AuditlogRule.search_count([("model_id", "=", model.id), ("name", "=", rule_name)]):
            continue
        AuditlogRule.create(
            {
                "name": rule_name,
                "model_id": model.id,
                "log_create": True,
                "log_write": True,
                "log_unlink": True,
                "log_read": False,
                "state": "draft",
            }
        )
        _logger.info("MCP Pro: created draft auditlog rule for %s.", model_name)
