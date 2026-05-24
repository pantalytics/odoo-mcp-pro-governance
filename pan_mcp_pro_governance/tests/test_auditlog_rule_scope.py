"""Tests for the audit rule scope filter (x_scope + x_user_ids / x_apikey_ids).

The decision lives in `_mcp_should_log_request`, which reads the current
`odoo.http.request`. TransactionCase has no request, so we patch it
directly with `unittest.mock` to simulate API-key vs browser channels.
"""

import datetime
from unittest import mock

from odoo.tests.common import TransactionCase


class TestAuditlogRuleScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env["auditlog.rule"]
        cls.ApiKey = cls.env["res.users.apikeys"].sudo()
        cls.partner_model = cls.env.ref("base.model_res_partner")

        cls.user_anna = cls.env["res.users"].create({"name": "Anna", "login": "anna_scope_test"})
        cls.user_bob = cls.env["res.users"].create({"name": "Bob", "login": "bob_scope_test"})

        # `res.users.apikeys` is `_auto = False` — use the canonical entry.
        future = datetime.datetime.now() + datetime.timedelta(days=1)
        cls.ApiKey.with_user(cls.user_anna)._generate("rpc", "Anna's Claude", future)
        cls.ApiKey.with_user(cls.user_bob)._generate("rpc", "Bob's n8n", future)
        cls.anna_key = cls.ApiKey.search(
            [("user_id", "=", cls.user_anna.id), ("name", "=", "Anna's Claude")],
            limit=1,
        )
        cls.bob_key = cls.ApiKey.search(
            [("user_id", "=", cls.user_bob.id), ("name", "=", "Bob's n8n")],
            limit=1,
        )

        # post_init_hook seeds a rule on res.partner. The unique constraint on
        # model_id means we cannot create another — reuse the seeded one.
        cls.rule = cls.Rule.search([("model_id", "=", cls.partner_model.id)], limit=1)
        if not cls.rule:
            cls.rule = cls.Rule.create({"name": "test scope", "model_id": cls.partner_model.id})

    def _mock_request(self, api_key_id=None):
        """Return a context manager that patches odoo.http.request."""
        req = mock.MagicMock()
        req.session.get.return_value = api_key_id
        return mock.patch(
            "odoo.addons.pan_mcp_pro_governance.models.auditlog_rule.request",
            req,
        )

    def test_scope_all_logs_everything(self):
        self.rule.x_scope = "all"
        with self._mock_request():
            self.assertTrue(self.rule._mcp_should_log_request(self.user_anna.id))
        with self._mock_request(api_key_id=self.anna_key.id):
            self.assertTrue(self.rule._mcp_should_log_request(self.user_anna.id))

    def test_scope_browser_excludes_api(self):
        self.rule.x_scope = "browser"
        with self._mock_request():
            self.assertTrue(self.rule._mcp_should_log_request(self.user_anna.id))
            self.assertTrue(self.rule._mcp_should_log_request(self.user_bob.id))
        with self._mock_request(api_key_id=self.anna_key.id):
            self.assertFalse(self.rule._mcp_should_log_request(self.user_anna.id))

    def test_scope_api_all_keys(self):
        """scope=api with empty keys list logs every API key call."""
        self.rule.x_scope = "api"
        self.rule.x_apikey_ids = [(5, 0, 0)]
        with self._mock_request(api_key_id=self.anna_key.id):
            self.assertTrue(self.rule._mcp_should_log_request(self.user_anna.id))
        with self._mock_request(api_key_id=self.bob_key.id):
            self.assertTrue(self.rule._mcp_should_log_request(self.user_bob.id))
        # No browser sessions logged in api scope.
        with self._mock_request():
            self.assertFalse(self.rule._mcp_should_log_request(self.user_anna.id))

    def test_scope_api_specific_keys(self):
        self.rule.x_scope = "api"
        self.rule.x_apikey_ids = [(6, 0, [self.anna_key.id])]
        with self._mock_request(api_key_id=self.anna_key.id):
            self.assertTrue(self.rule._mcp_should_log_request(self.user_anna.id))
        with self._mock_request(api_key_id=self.bob_key.id):
            self.assertFalse(self.rule._mcp_should_log_request(self.user_bob.id))
        with self._mock_request():
            self.assertFalse(self.rule._mcp_should_log_request(self.user_anna.id))

    def test_scope_users_covers_both_channels(self):
        """scope=users logs both browser and API key activity for listed users."""
        self.rule.x_scope = "users"
        self.rule.x_user_ids = [(6, 0, [self.user_anna.id])]
        # Anna's browser session: logged.
        with self._mock_request():
            self.assertTrue(self.rule._mcp_should_log_request(self.user_anna.id))
        # Anna's API key call: also logged (uid is Anna's id).
        with self._mock_request(api_key_id=self.anna_key.id):
            self.assertTrue(self.rule._mcp_should_log_request(self.user_anna.id))
        # Bob's browser session: not logged.
        with self._mock_request():
            self.assertFalse(self.rule._mcp_should_log_request(self.user_bob.id))
        # Bob's API key call: not logged.
        with self._mock_request(api_key_id=self.bob_key.id):
            self.assertFalse(self.rule._mcp_should_log_request(self.user_bob.id))

    def test_default_scope_is_all(self):
        """A freshly seeded rule has x_scope='all' and logs everything."""
        self.assertEqual(self.rule.x_scope, "all")
        with self._mock_request():
            self.assertTrue(self.rule._mcp_should_log_request(self.user_anna.id))
