"""Tests for the API-key extensions (x_role_id, x_state, lifecycle).

The `_check_credentials` override needs a live `odoo.http.request`, which
TransactionCase does not provide. That fail-closed path is covered by
manual smoke + the staging env. This file covers everything the model
can guarantee without an HTTP context: schema, defaults, ORM-level
constraint.

`res.users.apikeys` is `_auto = False` — no normal ORM create. We use
the canonical `_generate(scope, name, expiration_date)` entry point, the
same one the wizard calls.
"""

import datetime

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestApiKeyRoleBinding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ApiKey = cls.env["res.users.apikeys"].sudo()
        cls.Role = cls.env["res.users.role"]
        cls.role = cls.Role.create({"name": "MCP Test Role"})
        cls.user = cls.env["res.users"].create({
            "name": "MCP Key Owner",
            "login": "mcp_key_owner",
            "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
        })

    def _make_key(self):
        """Generate one key for self.user and return its ORM record.

        `_generate` always uses `self.env.user`. We override `env.user`
        for the call so the key belongs to our test user.
        """
        future = datetime.datetime.now() + datetime.timedelta(days=1)
        self.ApiKey.with_user(self.user)._generate("rpc", "test key", future)
        # _generate returns the raw key string, not the record. Fetch by
        # user+name (the test fixture creates exactly one).
        return self.ApiKey.search([
            ("user_id", "=", self.user.id),
            ("name", "=", "test key"),
        ], order="id desc", limit=1)

    def test_defaults_active(self):
        key = self._make_key()
        self.assertEqual(key.x_state, "active")
        self.assertFalse(key.x_role_id)
        self.assertEqual(key.x_use_count, 0)
        self.assertFalse(key.x_last_used)

    def test_role_must_belong_to_user(self):
        other_role = self.Role.create({"name": "Unassigned Role"})
        key = self._make_key()
        with self.assertRaises(ValidationError):
            key.x_role_id = other_role

    def test_role_assigned_to_user_is_accepted(self):
        key = self._make_key()
        key.x_role_id = self.role
        self.assertEqual(key.x_role_id, self.role)

    def test_state_transitions_are_plain_writes(self):
        # Suspended/revoked are how _check_credentials fails closed.
        # The migration in 19.0.0.3.0 relies on the same write path.
        key = self._make_key()
        key.x_state = "suspended"
        self.assertEqual(key.x_state, "suspended")
        key.x_state = "revoked"
        self.assertEqual(key.x_state, "revoked")
