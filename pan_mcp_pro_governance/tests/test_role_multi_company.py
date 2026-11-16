"""The role sync leaves core's multi-company group alone (issue #57).

Odoo links `base.group_multi_company` when a user gets a second company and
unlinks it at one (`res.users.write`). `set_groups_from_roles` replaces a
role-managed user's groups with the role's closure, and a role does not carry
that group, so it used to unlink it again right after core linked it. The
user could switch company but saw no company field on any record.
"""

from odoo.tests.common import TransactionCase

from .. import compat


class TestRoleSyncKeepsMultiCompanyGroup(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.multi_company = cls.env.ref("base.group_multi_company")
        cls.main_company = cls.env.ref("base.main_company")
        cls.other_company = cls.env["res.company"].create({"name": "MCP Second Company"})
        cls.role = cls.env["res.users.role"].create(
            {
                "name": "MCP Multi Company Test Role",
                "implied_ids": [(6, 0, [cls.group_user.id])],
            }
        )
        cls.user = cls.env["res.users"].create(
            {
                "name": "mcp_role_multi_company",
                "login": "mcp_role_multi_company",
                "company_id": cls.main_company.id,
                "company_ids": [(6, 0, [cls.main_company.id])],
                "role_line_ids": [(0, 0, {"role_id": cls.role.id})],
            }
        )

    def _has_multi_company(self):
        self.user.invalidate_recordset()
        return self.multi_company in compat.user_groups(self.user)

    def test_second_company_keeps_the_group(self):
        self.assertFalse(self._has_multi_company(), "precondition: one company")

        self.user.write({"company_ids": [(4, self.other_company.id)]})
        self.assertTrue(self._has_multi_company())

        # Any later write runs the role sync again; the group must survive it.
        self.user.write({"name": "mcp_role_multi_company renamed"})
        self.assertTrue(self._has_multi_company())
        self.assertIn(self.group_user, compat.user_groups(self.user))

    def test_back_to_one_company_drops_the_group(self):
        self.user.write({"company_ids": [(4, self.other_company.id)]})
        self.user.write({"company_ids": [(3, self.other_company.id)]})
        self.assertFalse(self._has_multi_company())
