"""Tests for the API-key creation wizard (res.users.apikeys.description).

We only test the validation paths our override adds — the part that runs
*before* `super().make_key()`. Calling super hits `@check_identity` and
the `_auto = False` apikeys table, neither friendly to TransactionCase.
"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestApiKeyWizardValidation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Role = cls.env["res.users.role"]
        cls.role = cls.Role.create({"name": "MCP Wizard Role"})
        cls.other_role = cls.Role.create({"name": "Not Mine"})
        cls.user = cls.env["res.users"].create(
            {
                "name": "Wizard User",
                "login": "wizard_user",
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )

    def _wizard(self, **overrides):
        values = {"name": "wizard test key", "duration": "30"}
        values.update(overrides)
        # sudo to bypass the wizard's own ACL; with_user to make
        # env.user.role_ids the test user's roles (what the compute reads).
        return self.env["res.users.apikeys.description"].with_user(self.user).sudo().create(values)

    def test_available_roles_are_users_roles(self):
        wiz = self._wizard()
        self.assertIn(self.role, wiz.x_available_role_ids)
        self.assertNotIn(self.other_role, wiz.x_available_role_ids)

    def test_role_required_to_create_key(self):
        wiz = self._wizard()
        with self.assertRaises(UserError):
            wiz.make_key()

    def test_role_must_be_assigned_to_user(self):
        wiz = self._wizard(x_role_id=self.other_role.id)
        with self.assertRaises(UserError):
            wiz.make_key()
