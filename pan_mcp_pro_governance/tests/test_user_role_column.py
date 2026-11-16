"""The users list shows each user's access role.

Odoo's ``mail`` defines ``res.users.role_ids`` (mention roles, ``res.role``)
and replaced the vendored field of the same name, so the list column was
always empty. The field is now ``x_role_ids``.
"""

from odoo.tests.common import TransactionCase


class TestUserRoleColumn(TransactionCase):
    def test_x_role_ids_follows_role_lines(self):
        role = self.env["res.users.role"].create({"name": "MCP Column Test Role"})
        user = self.env["res.users"].create({"name": "Column Test", "login": "col_test"})
        user.write({"role_line_ids": [(0, 0, {"role_id": role.id})]})
        self.assertEqual(user.x_role_ids, role)

    def test_list_view_uses_x_role_ids(self):
        arch = self.env["res.users"].get_view(self.env.ref("base.view_users_tree").id)["arch"]
        self.assertIn('name="x_role_ids"', arch)
