from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestApiCallLog(TransactionCase):
    def setUp(self):
        super().setUp()
        self.CallLog = self.env["mcp.governance.api.call.log"]
        self.AuditLog = self.env["mcp.governance.audit.log"]
        self.agent = self.env["mcp.governance.agent.identity"].create(
            {"name": "API Log Test Bot"}
        )

    def test_create_entry(self):
        entry = self.CallLog.create(
            {
                "x_agent_identity_id": self.agent.id,
                "x_user_id": self.env.user.id,
                "x_method": "POST",
                "x_path": "/mcp/tools/call",
                "x_tool_name": "search_records",
                "x_status_code": 200,
                "x_duration_ms": 142,
                "x_request_id": "req-abc-123",
            }
        )
        self.assertTrue(entry.id)
        self.assertIn("POST", entry.display_name)
        self.assertIn("search_records", entry.display_name)
        self.assertIn("200", entry.display_name)

    def test_entries_are_immutable(self):
        entry = self.CallLog.create({"x_method": "POST", "x_agent_identity_id": self.agent.id})
        with self.assertRaises(AccessError):
            entry.x_path = "/tampered"

    def test_entries_cannot_be_deleted(self):
        entry = self.CallLog.create({"x_method": "POST", "x_agent_identity_id": self.agent.id})
        with self.assertRaises(AccessError):
            entry.unlink()

    def test_audit_log_correlation(self):
        request_id = "req-correlated-42"
        call = self.CallLog.create(
            {
                "x_agent_identity_id": self.agent.id,
                "x_method": "POST",
                "x_tool_name": "create_record",
                "x_status_code": 200,
                "x_request_id": request_id,
            }
        )
        audit_a = self.AuditLog.create(
            {
                "x_agent_identity_id": self.agent.id,
                "x_action": "create",
                "x_request_id": request_id,
            }
        )
        audit_b = self.AuditLog.create(
            {
                "x_agent_identity_id": self.agent.id,
                "x_action": "update",
                "x_request_id": request_id,
            }
        )
        unrelated = self.AuditLog.create(
            {
                "x_agent_identity_id": self.agent.id,
                "x_action": "read",
                "x_request_id": "different-req",
            }
        )

        call.invalidate_recordset(["x_audit_log_ids", "x_audit_log_count"])
        self.assertEqual(call.x_audit_log_count, 2)
        related_ids = set(call.x_audit_log_ids.ids)
        self.assertIn(audit_a.id, related_ids)
        self.assertIn(audit_b.id, related_ids)
        self.assertNotIn(unrelated.id, related_ids)

    def test_action_open_audit_log_returns_filtered_action(self):
        request_id = "req-action-test"
        call = self.CallLog.create(
            {
                "x_agent_identity_id": self.agent.id,
                "x_method": "POST",
                "x_request_id": request_id,
            }
        )
        action = call.action_open_audit_log()
        self.assertEqual(action["res_model"], "mcp.governance.audit.log")
        self.assertIn(("x_request_id", "=", request_id), action["domain"])
