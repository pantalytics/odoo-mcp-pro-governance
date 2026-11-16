"""The role sync leaves core's multi-company group alone (issue #57).

Odoo links `base.group_multi_company` when a user gets a second company and
unlinks it at one (`res.users.write`). `set_groups_from_roles` replaces a
role-managed user's groups with the role's closure, and a role does not carry
that group, so it used to unlink it again right after core linked it. The
user could switch company but saw no company field on any record.

Reproduced on a real Odoo 19 before the fix: a role-managed user with two
companies did not have the group, a user without a role did.

Every path that runs the sync is covered, because each one used to strip the
group: a write on the user, an edit of the role, unlinking one of two role
lines, and the daily cron.
"""

from odoo.tests.common import TransactionCase

from .. import compat


class TestRoleSyncKeepsMultiCompanyGroup(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_partner_manager = cls.env.ref("base.group_partner_manager")
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
        return user

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
        user = self._two_company_user()
        user.write({"name": "mcp_mc_user renamed"})
        self.assertIn(self.multi_company, self._groups(user))

    def test_editing_the_role_keeps_the_group(self):
        user = self._two_company_user()
        self.role.write({"implied_ids": [(4, self.group_partner_manager.id)]})
        groups = self._groups(user)
        self.assertIn(self.group_partner_manager, groups, "the edit reached the user")
        self.assertIn(self.multi_company, groups)

    def test_unlinking_one_of_two_role_lines_keeps_the_group(self):
        second = self.Role.create(
            {"name": "MCP Second Role", "implied_ids": [(6, 0, [self.group_user.id])]}
        )
        user = self._two_company_user(roles=self.role | second)
        user.role_line_ids.filtered(lambda line: line.role_id == second).unlink()
        self.assertIn(self.multi_company, self._groups(user))

    def test_daily_cron_keeps_the_group(self):
        user = self._two_company_user()
        self.Role.cron_update_users()
        self.assertIn(self.multi_company, self._groups(user))
