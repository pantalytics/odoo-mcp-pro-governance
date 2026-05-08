from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestAuditLog(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Log = self.env["mcp.governance.audit.log"]
        self.agent = self.env["mcp.governance.agent.identity"].create({"name": "Audit Test Bot"})

    def test_create_entry(self):
        entry = self.Log.create(
            {
                "x_agent_identity_id": self.agent.id,
                "x_user_id": self.env.user.id,
                "x_action": "read",
                "x_description": "Listed invoices",
            }
        )
        self.assertTrue(entry.id)
        self.assertIn("read", entry.display_name)

    def test_entries_are_immutable(self):
        entry = self.Log.create({"x_action": "read", "x_agent_identity_id": self.agent.id})
        with self.assertRaises(AccessError):
            entry.x_description = "tampered"

    def test_entries_cannot_be_deleted(self):
        entry = self.Log.create({"x_action": "read", "x_agent_identity_id": self.agent.id})
        with self.assertRaises(AccessError):
            entry.unlink()
