"""Tests for the last-admin guard on role management.

The guard refuses any write that would leave zero active internal users
holding ``base.group_erp_manager`` ("Administration: Settings") — the
group that authorises editing ``res.users.role``.

We cover four ways a single transaction can wipe out the last role
manager:
    1. Removing the group directly from the user.
    2. Archiving the last user that holds the group.
    3. Editing a role so its implied groups no longer carry the group
       (cascades via OCA base_user_role's recompute on assignees).
    4. Unlinking a role that was the only carrier of the group.

Plus the happy paths: when another active manager exists, each of the
above is allowed.
"""

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRoleManagerGuard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Users = cls.env["res.users"].with_context(no_reset_password=True)
        cls.Role = cls.env["res.users.role"]
        cls.settings_group = cls.env.ref("base.group_erp_manager")
        cls.internal_group = cls.env.ref("base.group_user")

        # Demote every pre-existing settings-admin so each test starts
        # from a known "exactly one manager" baseline, then create that
        # one manager ourselves.
        existing = cls.Users.sudo().search(
            [("active", "=", True), ("group_ids", "in", cls.settings_group.id)]
        )
        existing.sudo().write({"group_ids": [(3, cls.settings_group.id)]})

        cls.sole_admin = cls.Users.sudo().create(
            {
                "name": "Sole Admin",
                "login": "sole_admin_guard_test",
                "group_ids": [
                    (4, cls.internal_group.id),
                    (4, cls.settings_group.id),
                ],
            }
        )

    def _make_extra_admin(self):
        return self.Users.sudo().create(
            {
                "name": "Backup Admin",
                "login": "backup_admin_guard_test",
                "group_ids": [
                    (4, self.internal_group.id),
                    (4, self.settings_group.id),
                ],
            }
        )

    # ---- direct group manipulation ----

    def test_remove_settings_group_from_last_admin_is_blocked(self):
        with self.assertRaises(ValidationError):
            self.sole_admin.sudo().write(
                {"group_ids": [(3, self.settings_group.id)]}
            )

    def test_remove_settings_group_when_backup_exists_is_allowed(self):
        self._make_extra_admin()
        self.sole_admin.sudo().write({"group_ids": [(3, self.settings_group.id)]})
        self.assertNotIn(self.settings_group, self.sole_admin.group_ids)

    # ---- archive ----

    def test_archive_last_admin_is_blocked(self):
        with self.assertRaises(ValidationError):
            self.sole_admin.sudo().write({"active": False})

    def test_archive_admin_when_backup_exists_is_allowed(self):
        self._make_extra_admin()
        self.sole_admin.sudo().write({"active": False})
        self.assertFalse(self.sole_admin.active)

    # ---- role-cascade: editing a role's implied groups ----

    def _make_admin_via_role(self, login_suffix):
        """Create a user whose only path to settings-group is via a role."""
        role = self.Role.sudo().create(
            {
                "name": f"Guard Test Role {login_suffix}",
                "implied_ids": [(6, 0, [self.settings_group.id])],
            }
        )
        user = self.Users.sudo().create(
            {
                "name": f"Role-Only Admin {login_suffix}",
                "login": f"role_only_admin_{login_suffix}",
                "role_line_ids": [(0, 0, {"role_id": role.id})],
            }
        )
        # OCA base_user_role replaces group_ids with role groups; verify.
        self.assertIn(self.settings_group, user.group_ids)
        return role, user

    def test_role_edit_removing_settings_group_from_sole_admin_is_blocked(self):
        # Replace the direct-group sole_admin with a role-only admin so
        # editing the role is the only path to losing settings access.
        # Need a backup admin before archiving sole_admin (otherwise the
        # archive itself trips the guard).
        backup = self._make_extra_admin()
        self.sole_admin.sudo().write({"active": False})
        role, _user = self._make_admin_via_role("edit_blocked")
        backup.sudo().write({"active": False})

        with self.assertRaises(ValidationError):
            role.sudo().write({"implied_ids": [(5, 0, 0)]})

    def test_role_edit_with_backup_admin_is_allowed(self):
        self._make_extra_admin()
        role, _user = self._make_admin_via_role("edit_allowed")
        role.sudo().write({"implied_ids": [(5, 0, 0)]})
        self.assertFalse(role.implied_ids)

    # ---- role unlink ----

    def test_unlink_role_carrying_sole_admin_settings_group_is_blocked(self):
        backup = self._make_extra_admin()
        self.sole_admin.sudo().write({"active": False})
        role, _user = self._make_admin_via_role("unlink_blocked")
        backup.sudo().write({"active": False})

        with self.assertRaises(ValidationError):
            role.sudo().unlink()

    def test_unlink_unused_role_is_allowed(self):
        role = self.Role.sudo().create({"name": "Unused Guard Test Role"})
        role.sudo().unlink()
        self.assertFalse(role.exists())
