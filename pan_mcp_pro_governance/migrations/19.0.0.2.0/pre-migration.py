"""Drop obsolete v0.1 governance tables.

v0.1 shipped two append-only log models that were never written to in
production. v0.2 replaces them with OCA `auditlog`. The tables are
guaranteed empty on real installs; drop unconditionally.
"""

import logging

_logger = logging.getLogger(__name__)


DROPPED_TABLES = [
    "mcp_governance_audit_log",
    "mcp_governance_api_call_log",
]


def migrate(cr, version):
    if not version:
        return
    for table in DROPPED_TABLES:
        cr.execute(
            "SELECT to_regclass(%s)",
            (f"public.{table}",),
        )
        if cr.fetchone()[0] is None:
            continue
        cr.execute(f"SELECT count(*) FROM {table}")  # noqa: S608 -- table from whitelist
        row_count = cr.fetchone()[0]
        if row_count:
            _logger.warning(
                "MCP Pro 19.0.0.2.0: %s has %d row(s); dropping anyway "
                "as part of v0.1 → v0.2 cleanup.",
                table,
                row_count,
            )
        cr.execute(f"DROP TABLE {table} CASCADE")  # noqa: S608
        _logger.info("MCP Pro 19.0.0.2.0: dropped %s.", table)
