"""Roles must not be assignable to users through the UI (issue #26).

OCA ``base_user_role`` (vendored as ``pan_mcp_user_role``) ships a
``role_line_ids`` page on the user form and a ``line_ids`` ("Users") page
on the role form. Assigning a role to a real employee makes
``set_groups_from_roles()`` *replace* that employee's groups with the
role's closure — documented OCA behaviour, but not something MCP Pro
promises. Our manifest promises one thing about roles: "bind each API key
to a single OCA user role", and ``res.users.apikeys.x_role_id`` reads
``role.group_id | role.implied_ids`` without the role ever being assigned
to the user.

So both assignment surfaces are removed from the views. The *model*
fields stay: this is a view-level change, pre-existing role lines keep
working, and the "access rights are managed by roles" alert still
explains them on the user form.
"""

from lxml import etree
from odoo.tests.common import TransactionCase


class TestRoleFormExposure(TransactionCase):
    """The role<->user assignment fields are not rendered anywhere."""

    def _arch(self, model, xmlid):
        """Return the combined, post-processed arch of ``xmlid`` as an etree."""
        view = self.env.ref(xmlid)
        arch = self.env[model].get_view(view.id, "form")["arch"]
        return etree.fromstring(arch)

    def test_role_line_ids_absent_from_user_form(self):
        """`role_line_ids` must not be reachable on the res.users form."""
        tree = self._arch("res.users", "base.view_users_form")
        self.assertFalse(
            tree.xpath("//field[@name='role_line_ids']"),
            "res.users form still exposes role_line_ids — assigning a role to a "
            "user replaces that user's groups. See issue #26 and "
            "pan_mcp_user_role/views/user.xml.",
        )
        self.assertFalse(
            tree.xpath("//field[@name='role_ids']"),
            "res.users form still exposes role_ids (the helper the removed "
            "'User Roles' page used). See issue #26.",
        )

    def test_users_list_absent_from_role_form(self):
        """The role form must not offer the OCA 'Users' assignment list."""
        tree = self._arch("res.users.role", "pan_mcp_user_role.view_res_users_role_form")
        self.assertFalse(
            tree.xpath("//field[@name='line_ids']"),
            "res.users.role form still exposes line_ids — a role is an API-key "
            "scope, not a way to manage a person's rights. See issue #26 and "
            "pan_mcp_user_role/views/role.xml.",
        )

    def test_role_form_still_shows_its_groups(self):
        """Regression guard: removing the Users page must not touch the Groups page."""
        tree = self._arch("res.users.role", "pan_mcp_user_role.view_res_users_role_form")
        self.assertTrue(
            tree.xpath("//field[@name='implied_ids']"),
            "The role form lost its Access Rights widget on implied_ids.",
        )

    def test_assignment_fields_still_exist_on_the_models(self):
        """This is a view-level change — the OCA fields stay on the models.

        Pre-existing role lines (seeded before the upgrade, or created by
        the ``wizard.create.role.from.user`` wizard) must keep resolving.
        """
        self.assertIn("role_line_ids", self.env["res.users"]._fields)
        self.assertIn("line_ids", self.env["res.users.role"]._fields)

    def test_create_from_user_wizard_cannot_assign(self):
        """The Action-menu wizard must not offer role assignment (issue #26).

        `wizard.create.role.from.user` is bound to the user form, and its
        upstream `assign_to_user` option defaulted to True -- reopening the
        exact assignment path this issue closes, from a menu that is still
        visible. Reading a user's groups into a fresh role stays useful, so
        the wizard survives without the option.
        """
        self.assertNotIn(
            "assign_to_user",
            self.env["wizard.create.role.from.user"]._fields,
            "the wizard must not carry an assign-to-user option",
        )
        user = self.env["res.users"].create(
            {"name": "mcp_wizard_probe", "login": "mcp_wizard_probe"}
        )
        wizard = (
            self.env["wizard.create.role.from.user"]
            .with_context(active_ids=[user.id], active_model="res.users")
            .create({"name": "MCP Wizard Probe Role"})
        )
        wizard.create_from_user()
        user.invalidate_recordset()
        self.assertFalse(
            user.role_line_ids,
            "creating a role from a user must not assign that role to them",
        )
