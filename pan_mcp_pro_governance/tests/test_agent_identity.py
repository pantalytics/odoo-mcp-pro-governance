from odoo.tests.common import TransactionCase


class TestAgentIdentity(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Identity = self.env["mcp.governance.agent.identity"]

    def test_create_defaults_to_draft(self):
        agent = self.Identity.create({"name": "Test Bot"})
        self.assertEqual(agent.state, "draft")
        self.assertEqual(agent.x_provider, "anthropic")
        self.assertEqual(agent.x_owner_id, self.env.user)

    def test_lifecycle_transitions(self):
        agent = self.Identity.create({"name": "Lifecycle Bot"})
        agent.action_activate()
        self.assertEqual(agent.state, "active")
        agent.action_suspend()
        self.assertEqual(agent.state, "suspended")
        agent.action_revoke()
        self.assertEqual(agent.state, "revoked")
        self.assertFalse(agent.active)

    def test_name_must_be_unique(self):
        self.Identity.create({"name": "Unique Bot"})
        with self.assertRaises(Exception):
            self.Identity.create({"name": "Unique Bot"})
