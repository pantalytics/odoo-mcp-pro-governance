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


def post_init_hook(env):
    """Seed auditlog rules for installed AI-action target models."""
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
