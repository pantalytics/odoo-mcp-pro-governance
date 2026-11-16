"""Administrator is a choice per user, the role sync leaves it alone (#60).

Reported on a customer production: a user with the role "Accounting" was set
to Administrator with the Role radio on the user form. Save, and the form
jumped back to User. `res.users.write` runs `set_groups_from_roles`, which
replaced the groups with the role's closure, and that closure did not hold
`base.group_system`.

Decision in #60: `base.group_system` stays a field on the user, like in
standard Odoo. The sync never adds or removes it. A user who has it keeps
everything it implies, so no role edit or cron run can lock an administrator
out.
"""

from odoo import fields
from odoo.tests.common import TransactionCase

from .. import compat


class TestRoleSyncLeavesAdministratorAlone(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_system = cls.env.ref("base.group_system")
        cls.group_erp_manager = cls.env.ref("base.group_erp_manager")
        cls.Role = cls.env["res.users.role"]
        cls.role = cls.Role.create(
            {"name": "MCP Admin Flag Role", "implied_ids": [(6, 0, [cls.group_user.id])]}
        )
        cls.admin_role = cls.Role.create(
            {"name": "MCP Admin Flag System Role", "implied_ids": [(6, 0, [cls.group_system.id])]}
        )

    def _user(self, login, role):
        return self.env["res.users"].create(
            {"name": login, "login": login, "role_line_ids": [(0, 0, {"role_id": role.id})]}
        )

    def _groups(self, user):
        user.invalidate_recordset()
        return compat.user_groups(user)

    def _set_admin(self, user, on):
        command = fields.Command.link if on else fields.Command.unlink
        user.write({compat.USER_GROUPS_FIELD: [command(self.group_system.id)]})

    def test_making_a_role_user_administrator_sticks(self):
        user = self._user("mcp_admin_flag_promote", self.role)
        self.assertNotIn(self.group_system, self._groups(user), "precondition")
        self._set_admin(user, True)
        self.assertIn(self.group_system, self._groups(user))
        self.assertIn(self.group_erp_manager, self._groups(user), "admin keeps its closure")

    def test_administrator_survives_role_edit_and_cron(self):
        user = self._user("mcp_admin_flag_keep", self.role)
        self._set_admin(user, True)
        self.role.write({"name": "MCP Admin Flag Role (edited)"})
        self.Role.cron_update_users()
        self.assertIn(self.group_system, self._groups(user))

    def test_removing_administrator_sticks(self):
        user = self._user("mcp_admin_flag_demote", self.role)
        self._set_admin(user, True)
        self._set_admin(user, False)
        groups = self._groups(user)
        self.assertNotIn(self.group_system, groups)
        self.assertNotIn(
            self.group_erp_manager, groups, "groups that came only from admin go with it"
        )

    def test_role_does_not_hand_out_administrator(self):
        user = self._user("mcp_admin_flag_role", self.admin_role)
        self.assertNotIn(self.group_system, self._groups(user))
