"""Drop the parked agent-identity model.

The model `mcp.governance.agent.identity` was kept since v0.4 behind a
dev-mode menu, in anticipation of future governance features. It was
never used in production: OCA `auditlog` already attributes every
inbound call to a `res.users`, which covers current attribution needs.

ir.model / ir.model.fields / ir.ui.view / ir.actions.act_window / ACL
rows tied to module XML ids are cleaned up automatically when the
upgrade re-runs data files. We only need to drop the physical table —
Odoo does not auto-drop tables when a model disappears from code.

ADR-004 is hereby superseded.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT to_regclass('public.mcp_governance_agent_identity')")
    if cr.fetchone()[0] is None:
        return
    cr.execute("SELECT count(*) FROM mcp_governance_agent_identity")
    row_count = cr.fetchone()[0]
    if row_count:
        _logger.warning(
            "MCP Pro 19.0.1.10.0: mcp_governance_agent_identity has %d row(s); "
            "dropping anyway — the model is being removed.",
            row_count,
        )
    cr.execute("DROP TABLE mcp_governance_agent_identity CASCADE")
    _logger.info("MCP Pro 19.0.1.10.0: dropped mcp_governance_agent_identity.")
