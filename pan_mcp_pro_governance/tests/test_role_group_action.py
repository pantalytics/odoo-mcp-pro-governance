"""Regression test for the "View Roles" button on the group form.

``res.groups.action_view_roles`` (vendored from OCA ``base_user_role``,
see ``pan_mcp_user_role/models/res_groups.py``) has two branches. With
several roles it only sets a domain; with *exactly one* role it resolves
the role form view by XML id and jumps straight to that record.

That second branch still carried the pre-rename ``base_user_role.``
prefix, which no longer exists in this bundle, so the button raised
``ValueError: External ID not found in the system`` (issue #29). Because
only the single-role branch looks the view up, the crash surfaced late.

This test drives that exact branch.
"""

from odoo.tests.common import TransactionCase


class TestRoleGroupAction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.role = cls.env["res.users.role"].create(
            {
                "name": "MCP Group Action Test Role",
                "implied_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        # A role _inherits res.groups, so it owns a group whose `role_id`
        # inverse points straight back at it: exactly one role, no parents.
        cls.group = cls.role.group_id

    def test_role_form_xml_id_exists(self):
        """The renamed XML id is the one the action must reference."""
        view = self.env.ref("pan_mcp_user_role.view_res_users_role_form")
        self.assertEqual(view._name, "ir.ui.view")
        self.assertEqual(view.model, "res.users.role")

    def test_action_view_roles_single_role_resolves_form_view(self):
        """One role on the group -> an action pointing at that role's form."""
        self.assertEqual(self.group.role_ids, self.role)

        action = self.group.action_view_roles()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "res.users.role")
        self.assertEqual(action["res_id"], self.role.id)

        form_view_id = self.env.ref("pan_mcp_user_role.view_res_users_role_form").id
        self.assertEqual(
            action["views"][0],
            (form_view_id, "form"),
            "the form view must come first so the action opens the role record",
        )
        # The rewritten view list keeps one form entry only — the resolved one.
        form_entries = [view for view in action["views"] if view[1] == "form"]
        self.assertEqual(form_entries, [(form_view_id, "form")])

    def test_action_view_roles_multiple_roles_uses_domain(self):
        """Sanity guard on the other branch: domain, no form lookup."""
        other_group = self.env["res.groups"].create({"name": "MCP Action Test Parent"})
        # `parent_ids` is the inverse of `implied_ids`: make two roles imply
        # the same group so that group resolves to more than one role.
        role_b = self.env["res.users.role"].create({"name": "MCP Group Action Role B"})
        (self.role | role_b).write({"implied_ids": [(4, other_group.id)]})
        other_group.invalidate_recordset()

        self.assertEqual(len(other_group.role_ids), 2)

        action = other_group.action_view_roles()

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(sorted(action["domain"][0][2]), sorted((self.role | role_b).ids))
        self.assertFalse(action.get("res_id"))
