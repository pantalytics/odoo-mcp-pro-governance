"""Unlinking a role line must not wipe the user's groups (issue #27).

Boris van der Hoeven (Pressure Control Solutions) reported this from a
17.0 staging database; it reproduces on 19.0 the same way. The table he
attached is what `test_unlink_last_role_line_leaves_groups_untouched`
below reproduces verbatim:

    groups before                 : 74   share = False
    groups after creating line    : 74   share = False
    groups after unlink of line   :  0   share = True

`res.users.role.line.unlink()` calls `set_groups_from_roles(force=True)`,
and `force` used to bypass the "no role lines -> leave the groups alone"
guard in `pan_mcp_user_role/models/user.py`. The user is role-less by the
time the guard runs, so the computed group set is empty and every group
is unlinked — which also flips `share` to True, because `share` is
"not a member of base.group_user".

The second test pins the other half of the contract: `force` exists so
that editing or deleting a role recomputes the users carrying it. Users
that *still* have role lines must keep being recomputed exactly as
before, so a fix that simply stopped recomputing on unlink would be
wrong too.
"""

from odoo.tests.common import TransactionCase

from .. import compat


class TestRoleLineUnlinkKeepsGroups(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_partner_manager = cls.env.ref("base.group_partner_manager")
        cls.RoleLine = cls.env["res.users.role.line"]
        cls.role = cls.env["res.users.role"].create(
            {
                "name": "MCP Unlink Test Role",
                "implied_ids": [(6, 0, [cls.group_user.id])],
            }
        )

    def _new_user(self, login, groups):
        """A throwaway internal user with an explicit, role-free group set.

        `role_line_ids` is forced empty: a role flagged `is_default` in the
        database would otherwise be seeded onto the user by
        `_default_role_lines`, and this test is about users that carry no
        role lines at all.
        """
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "role_line_ids": [],
                compat.USER_GROUPS_FIELD: [(6, 0, groups.ids)],
            }
        )

    def test_unlink_last_role_line_leaves_groups_untouched(self):
        """No roles means "leave groups alone" — also on the force path."""
        user = self._new_user(
            "mcp_role_unlink_victim",
            self.group_user | self.group_partner_manager,
        )
        self.assertFalse(user.role_line_ids, "precondition: user starts role-less")
        groups_before = set(compat.user_groups(user).ids)
        self.assertTrue(groups_before)
        self.assertFalse(user.share)

        line = self.RoleLine.create({"user_id": user.id, "role_id": self.role.id})
        # Creating the line does not recompute by itself — the damage used to
        # land later, on the unlink (or on any routine write to the user).
        self.assertEqual(set(compat.user_groups(user).ids), groups_before)

        line.unlink()
        user.invalidate_recordset()

        self.assertEqual(
            set(compat.user_groups(user).ids),
            groups_before,
            "unlinking the last role line must not touch the user's groups",
        )
        self.assertFalse(user.share, "the user must not be downgraded to a share user")

    def test_unlink_one_of_two_role_lines_still_recomputes(self):
        """A user that still has role lines keeps being synced from its roles.

        This is what `force=True` is for on the unlink paths; the fix for
        issue #27 must not disable it.
        """
        other_role = self.env["res.users.role"].create(
            {
                "name": "MCP Unlink Test Role 2",
                "implied_ids": [(6, 0, [self.group_user.id, self.group_partner_manager.id])],
            }
        )
        user = self._new_user("mcp_role_unlink_survivor", self.group_user)
        kept = self.RoleLine.create({"user_id": user.id, "role_id": self.role.id})
        dropped = self.RoleLine.create({"user_id": user.id, "role_id": other_role.id})

        # Sync the user up to both roles first (this is the ordinary,
        # non-forced path: the user has role lines).
        user.set_groups_from_roles()
        user.invalidate_recordset()
        self.assertIn(self.group_partner_manager.id, compat.user_groups(user).ids)

        dropped.unlink()
        user.invalidate_recordset()

        self.assertTrue(kept.exists())
        group_ids = set(compat.user_groups(user).ids)
        self.assertNotIn(
            self.group_partner_manager.id,
            group_ids,
            "groups of the removed role must be dropped while role lines remain",
        )
        self.assertIn(self.group_user.id, group_ids)
        self.assertFalse(user.share)
