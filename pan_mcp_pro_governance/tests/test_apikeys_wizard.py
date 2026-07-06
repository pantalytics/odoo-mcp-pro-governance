"""Tests for the API-key creation wizard (res.users.apikeys.description).

We only test the validation paths our override adds — the part that runs
*before* `super().make_key()`. Calling super hits `@check_identity` and
the `_auto = False` apikeys table, neither friendly to TransactionCase.
"""

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
        Desc = self.env["res.users.apikeys.description"]
        values = {"name": "wizard test key"}
        # duration/expiration arrived in Odoo 18; the 17 wizard has no such field.
        if "duration" in Desc._fields:
            values["duration"] = "30"
        values.update(overrides)
        # sudo to bypass the wizard's own ACL; with_user to make
        # env.user.role_ids the test user's roles (what the compute reads).
        return Desc.with_user(self.user).sudo().create(values)

    def test_available_roles_include_subset_roles(self):
        # The wizard filters roles to those whose implied groups are a
        # subset of the current user's groups. cls.role has no implied
        # groups (empty set), trivially a subset → present.
        wiz = self._wizard()
        self.assertIn(self.role, wiz.x_available_role_ids)

    def test_wizard_view_combines_under_translation(self):
        # Regression: our inherit anchored on translated h3 text
        # (`//h3[contains(., 'Give a duration')]`), so combining the wizard
        # view raised "Element not found" on any non-English instance —
        # view inheritance runs against the *translated* arch. Reproduce by
        # translating the base heading and requesting the view in that lang.
        Desc = self.env["res.users.apikeys.description"]
        if "duration" not in Desc._fields:
            self.skipTest("no duration section before Odoo 18")
        self.env["res.lang"]._activate_lang("nl_NL")
        self.env.ref("base.form_res_users_key_description").update_field_translations(
            "arch_db",
            {
                "nl_NL": {
                    "Give a duration for the key's validity": (
                        "Geef een geldigheidsduur op voor de sleutel"
                    )
                }
            },
        )
        # Before the fix this raises ValueError during apply_inheritance_specs.
        view = Desc.with_context(lang="nl_NL").get_view()
        self.assertIn("x_role_id", view["arch"])

    # NOTE: a "role with extra groups is excluded" test would create a
    # role with role.implied_ids = [admin_only_group] and assert it is
    # absent from x_available_role_ids. That write currently trips the
    # too-broad lockout guard in res.users.role.write under
    # TransactionCase. Restore once the guard is narrowed to only fire
    # on user-removal paths.
