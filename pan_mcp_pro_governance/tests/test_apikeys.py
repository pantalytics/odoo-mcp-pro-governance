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

from odoo.tests.common import TransactionCase

from .. import compat


class TestApiKeyRoleBinding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ApiKey = cls.env["res.users.apikeys"].sudo()
        cls.Role = cls.env["res.users.role"]
        # Imply base.group_user so the key owner is a realistic internal user.
        # A user with zero groups trips a latent Odoo 18 core bug in
        # res.users._check_expiration_date (max() over an empty groups set)
        # during API-key generation; every real internal user has group_user.
        cls.role = cls.Role.create(
            {
                "name": "MCP Test Role",
                "implied_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.user = cls.env["res.users"].create(
            {
                "name": "MCP Key Owner",
                "login": "mcp_key_owner",
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )

    def _make_key(self):
        """Generate one key for self.user and return its ORM record.

        `_generate` always uses `self.env.user`. We override `env.user`
        for the call so the key belongs to our test user.
        """
        api = self.ApiKey.with_user(self.user)
        if compat.ODOO_VERSION >= 18:
            # Odoo 18 added the expiration_date argument to _generate.
            future = datetime.datetime.now() + datetime.timedelta(days=1)
            api._generate("rpc", "test key", future)
        else:
            api._generate("rpc", "test key")
        # _generate returns the raw key string, not the record. Fetch by
        # user+name (the test fixture creates exactly one).
        return self.ApiKey.search(
            [
                ("user_id", "=", self.user.id),
                ("name", "=", "test key"),
            ],
            order="id desc",
            limit=1,
        )

    def test_defaults_active(self):
        key = self._make_key()
        self.assertEqual(key.x_state, "active")
        self.assertFalse(key.x_role_id)
        self.assertEqual(key.x_use_count, 0)
        self.assertFalse(key.x_last_used)

    def test_role_with_subset_groups_is_accepted(self):
        # The constraint requires role.all_implied_ids ⊆ user.group_ids.
        # cls.role has no implied groups (empty set), which is trivially
        # a subset of any user's groups, so this assignment is accepted.
        key = self._make_key()
        key.x_role_id = self.role
        self.assertEqual(key.x_role_id, self.role)

    # NOTE: a proper "role with extra groups is rejected" test would
    # mutate role.implied_ids, but the lockout guard on res.users.role
    # write fires false-positives in TransactionCase (no admin with
    # base.group_erp_manager visible in the test DB). Manual UI test on
    # localhost has validated the constraint; tighten the guard then
    # restore a unit test here. See findings 2026-05-21.

    def test_state_transitions_are_plain_writes(self):
        # Suspended/revoked are how _check_credentials fails closed.
        # The migration in 19.0.0.3.0 relies on the same write path.
        key = self._make_key()
        key.x_state = "suspended"
        self.assertEqual(key.x_state, "suspended")
        key.x_state = "revoked"
        self.assertEqual(key.x_state, "revoked")


class TestApiKeyFieldsOnTotpDevice(TransactionCase):
    """`auth_totp.device` inherits `res.users.apikeys` by prototype, so Odoo
    copies our x_* fields onto its own `auth_totp_device` table. The columns
    must physically exist there too, otherwise any ORM read of a TOTP device
    (e.g. the user form snapshotting `totp_trusted_device_ids` during an
    onchange) raises `UndefinedColumn: auth_totp_device.x_role_id`.

    Regression for the DCBO / Mil Cuyvers report, 2026-07-09.
    """

    def _columns(self, table):
        self.env.cr.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s",
            (table,),
        )
        return {row[0] for row in self.env.cr.fetchall()}

    def test_x_columns_exist_on_totp_device_table(self):
        if "auth_totp.device" not in self.env.registry:
            self.skipTest("auth_totp not installed in this database")
        expected = {"x_role_id", "x_state", "x_last_used", "x_use_count"}
        columns = self._columns("auth_totp_device")
        missing = expected - columns
        self.assertFalse(
            missing,
            f"auth_totp_device is missing inherited apikeys columns: {missing}",
        )

    def test_reading_inherited_field_does_not_crash(self):
        if "auth_totp.device" not in self.env.registry:
            self.skipTest("auth_totp not installed in this database")
        # A bare search_read of the leaked field is enough to hit the SQL
        # column that used to be absent; it must not raise.
        self.env["auth_totp.device"].sudo().search_read(
            [], ["x_role_id", "x_state"], limit=1
        )
