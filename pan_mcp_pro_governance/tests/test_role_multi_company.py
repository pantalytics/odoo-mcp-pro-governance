"""The role sync leaves core's multi-company group alone (issue #57).

Odoo links `base.group_multi_company` when a user gets a second company and
unlinks it at one (`res.users.write`). `set_groups_from_roles` replaces a
role-managed user's groups with the role's closure, and a role does not carry
that group, so it used to unlink it again right after core linked it. The
user could switch company but saw no company field on any record.

Reproduced on a real Odoo 19 before the fix: a role-managed user with two
companies did not have the group, a user without a role did.

The sync applies core's rule itself (group if and only if more than one
company), so every path that runs it keeps the group, and the 3-hourly cron
repairs users who lost it before the fix. Each path test also shows the sync
really ran: a group outside the role, slipped in past the sync, is gone again.
"""

from odoo.tests.common import TransactionCase

from .. import compat


class TestRoleSyncKeepsMultiCompanyGroup(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        # A group no role here carries, so only the sync can take it away.
        cls.stray = cls.env["res.groups"].create({"name": "MCP stray group"})
        cls.multi_company = cls.env.ref("base.group_multi_company")
        cls.main_company = cls.env.ref("base.main_company")
        cls.other_company = cls.env["res.company"].create({"name": "MCP Second Company"})
        cls.Role = cls.env["res.users.role"]
        cls.role = cls.Role.create(
            {
                "name": "MCP Multi Company Test Role",
                "implied_ids": [(6, 0, [cls.group_user.id])],
            }
        )

    def _user(self, login, companies, roles):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "company_id": self.main_company.id,
                "company_ids": [(6, 0, companies.ids)],
                "role_line_ids": [(0, 0, {"role_id": r.id}) for r in roles],
            }
        )

    def _groups(self, user):
        user.invalidate_recordset()
        return compat.user_groups(user)

    def _two_company_user(self, login="mcp_mc_user", roles=None):
        user = self._user(login, self.main_company, roles or self.role)
        user.write({"company_ids": [(4, self.other_company.id)]})
        self.assertIn(self.multi_company, self._groups(user), "precondition")
        return user

    def _slip_in(self, user, group, present=True):
        """Set one group on `user` behind the ORM's back, the way a database
        looks after a sync that ran before this fix. Every ORM write on
        res.users would run the sync itself."""
        if present:
            self.env.cr.execute(
                "INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (group.id, user.id),
            )
        else:
            self.env.cr.execute(
                "DELETE FROM res_groups_users_rel WHERE gid = %s AND uid = %s", (group.id, user.id)
            )
        self.env.invalidate_all()
        self.env.registry.clear_cache()

    def _assert_sync_ran(self, user):
        groups = self._groups(user)
        self.assertNotIn(self.stray, groups, "the sync did not run")
        self.assertIn(self.multi_company, groups)

    # -- core decides, the sync follows ------------------------------------

    def test_second_company_keeps_the_group(self):
        user = self._user("mcp_mc_one", self.main_company, self.role)
        self.assertNotIn(self.multi_company, self._groups(user), "precondition: one company")

        user.write({"company_ids": [(4, self.other_company.id)]})
        self.assertIn(self.multi_company, self._groups(user))
        self.assertIn(self.group_user, self._groups(user), "the role's groups stay too")

    def test_back_to_one_company_drops_the_group(self):
        user = self._two_company_user()
        user.write({"company_ids": [(3, self.other_company.id)]})
        self.assertNotIn(self.multi_company, self._groups(user))

    def test_created_with_two_companies_has_the_group(self):
        user = self._user("mcp_mc_two", self.main_company | self.other_company, self.role)
        self.assertIn(self.multi_company, self._groups(user))

    def test_a_role_cannot_hand_out_the_group(self):
        """A role carrying the group does not give it to a one-company user:
        it follows the companies, never the role."""
        self.role.write({"implied_ids": [(4, self.multi_company.id)]})
        user = self._user("mcp_mc_role_carries", self.main_company, self.role)
        self.assertNotIn(self.multi_company, self._groups(user))

    # -- every path that re-runs the sync keeps it -------------------------

    def test_later_write_on_the_user_keeps_the_group(self):
        # Only the group is asserted here, not that the sync ran: after the
        # auditlog tests in the same process, res.users.write is base's own
        # (pantalytics/odoo-mcp-pro-governance#59), so a user write skips every
        # override. The other path tests show the sync ran.
        user = self._two_company_user()
        user.write({"name": "mcp_mc_user renamed"})
        self.assertIn(self.multi_company, self._groups(user))

    def test_editing_the_role_keeps_the_group(self):
        user = self._two_company_user()
        self._slip_in(user, self.stray)
        self.role.write({"name": "MCP Multi Company Test Role renamed"})
        self._assert_sync_ran(user)

    def test_unlinking_one_of_two_role_lines_keeps_the_group(self):
        second = self.Role.create(
            {"name": "MCP Second Role", "implied_ids": [(6, 0, [self.group_user.id])]}
        )
        user = self._two_company_user(roles=self.role | second)
        self._slip_in(user, self.stray)
        user.role_line_ids.filtered(lambda line: line.role_id == second).unlink()
        self._assert_sync_ran(user)

    def test_cron_keeps_the_group(self):
        user = self._two_company_user()
        self._slip_in(user, self.stray)
        self.Role.cron_update_users()
        self._assert_sync_ran(user)

    # -- users broken before the fix are repaired --------------------------

    def test_cron_gives_the_group_back_to_a_user_who_lost_it(self):
        user = self._two_company_user()
        self._slip_in(user, self.multi_company, present=False)
        self.assertNotIn(
            self.multi_company, self._groups(user), "precondition: broken as before #57"
        )

        self.Role.cron_update_users()
        self.assertIn(self.multi_company, self._groups(user))

    def test_cron_takes_the_group_from_a_one_company_user(self):
        user = self._user("mcp_mc_stale", self.main_company, self.role)
        self._slip_in(user, self.multi_company)
        self.Role.cron_update_users()
        self.assertNotIn(self.multi_company, self._groups(user))
