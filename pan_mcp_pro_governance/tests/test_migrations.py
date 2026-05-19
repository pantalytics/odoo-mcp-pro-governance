"""Tests for the migration scripts.

The v0.2 pre-migration drops two legacy v0.1 tables; once the test DB
has installed v0.3 those tables must not exist. The v0.3 post-migration
suspends role-less keys — that path is covered indirectly by
test_apikeys.py (x_state default is 'active'; the migration only matters
on upgrade from a pre-existing DB).
"""

from odoo.tests.common import TransactionCase


class TestLegacyTablesDropped(TransactionCase):
    def test_v01_log_tables_are_gone(self):
        self.env.cr.execute(
            "SELECT to_regclass(%s), to_regclass(%s)",
            ("public.mcp_governance_audit_log", "public.mcp_governance_api_call_log"),
        )
        audit, api_call = self.env.cr.fetchone()
        self.assertIsNone(
            audit, "mcp_governance_audit_log should be dropped by 19.0.0.2.0 migration"
        )
        self.assertIsNone(
            api_call, "mcp_governance_api_call_log should be dropped by 19.0.0.2.0 migration"
        )
