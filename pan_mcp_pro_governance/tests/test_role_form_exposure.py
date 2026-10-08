"""Role or rights on the user form, never both.

A user's rights come from a role (``role_line_ids`` on the Access Rights
page) or from the standard group widget, and the form shows one of the
two. ``show_alert`` (OCA: "has an enabled role line") is the switch that
hides the widget. The role form has no "Users" page: assignment happens
on the user, the role only counts its users and keys in smart buttons.

The API-key wizard and the "API Key Ready" form follow the same rule:
one heading and one field per step, help in the field tooltip, no
banners, no external links.
"""

import datetime

from lxml import etree
from odoo.tests.common import TransactionCase

from .. import compat


class TestRoleFormExposure(TransactionCase):
    def _arch(self, model, xmlid):
        """Return the combined, post-processed arch of ``xmlid`` as an etree."""
        view = self.env.ref(xmlid)
        arch = self.env[model].get_view(view.id, "form")["arch"]
        return etree.fromstring(arch)

    def _make_role(self, name, groups):
        return self.env["res.users.role"].create(
            {"name": name, "implied_ids": [(6, 0, [g.id for g in groups])]}
        )

    # -- user form ----------------------------------------------------------

    def test_role_lines_on_access_rights_page(self):
        tree = self._arch("res.users", "base.view_users_form")
        nodes = tree.xpath("//page[@name='access_rights']//field[@name='role_line_ids']")
        self.assertEqual(len(nodes), 1, "role_line_ids must sit on the Access Rights page")
        self.assertIn("MCP Pro Governance", nodes[0].get("help") or "")
        self.assertFalse(
            tree.xpath("//page[@name='access_rights']//div[hasclass('alert')]"),
            "the OCA 'managed by roles' alert must be gone",
        )

    def test_group_widget_hidden_when_a_role_is_set(self):
        tree = self._arch("res.users", "base.view_users_form")
        widgets = tree.xpath(
            f"//page[@name='access_rights']//field[@name='{compat.USER_GROUPS_FIELD}']"
        )
        self.assertTrue(widgets, "the standard group widget must still be in the view")
        # get_view rewrites a node whose `groups` the viewer lacks to
        # invisible="1" (the debug-only twin); the other one must carry the
        # switch.
        switched = [n for n in widgets if "show_alert" in (n.get("invisible") or "")]
        self.assertTrue(switched, "no group widget hides when a role line is enabled")
        for node in widgets:
            self.assertTrue(
                node in switched or node.get("invisible") == "1",
                "a group widget stays visible with a role line enabled",
            )

    def test_show_alert_follows_role_lines(self):
        user = self.env["res.users"].create({"name": "mcp_probe", "login": "mcp_probe"})
        self.assertFalse(user.show_alert)
        role = self._make_role("MCP Probe Role", [self.env.ref("base.group_user")])
        user.write({"role_line_ids": [(0, 0, {"role_id": role.id})]})
        self.assertTrue(user.show_alert)
        self.assertIn(self.env.ref("base.group_user"), compat.user_groups(user))
        user.role_line_ids.unlink()
        self.assertFalse(user.show_alert)
        # Removing the role keeps the groups (issue #27).
        self.assertIn(self.env.ref("base.group_user"), compat.user_groups(user))

    # -- role form ----------------------------------------------------------

    def test_role_form_counts_instead_of_listing(self):
        tree = self._arch("res.users.role", "pan_mcp_user_role.view_res_users_role_form")
        self.assertFalse(
            tree.xpath("//field[@name='line_ids']"),
            "the role form must not carry the OCA 'Users' assignment list",
        )
        self.assertTrue(tree.xpath("//button[@name='show_role_user_ids']"))
        self.assertTrue(tree.xpath("//button[@name='action_mcp_show_apikeys']"))
        self.assertTrue(
            tree.xpath("//field[@name='implied_ids']"),
            "the role form lost its Access Rights widget on implied_ids",
        )
        self.assertFalse(tree.xpath("//a[starts-with(@href, 'http')]"))

    def test_role_smart_button_counts(self):
        role = self._make_role("MCP Count Role", [self.env.ref("base.group_user")])
        self.assertEqual(role.user_count, 0)
        self.assertEqual(role.x_apikey_count, 0)
        user = self.env["res.users"].create(
            {
                "name": "mcp_count",
                "login": "mcp_count",
                "role_line_ids": [(0, 0, {"role_id": role.id})],
            }
        )
        role.invalidate_recordset()
        self.assertEqual(role.user_count, 1)
        self.assertIn(user, role.role_user_ids)
        api = self.env["res.users.apikeys"].with_user(user)
        if compat.ODOO_VERSION >= 18:
            api._generate("rpc", "k", datetime.datetime.now() + datetime.timedelta(days=1))
        else:
            api._generate("rpc", "k")
        self.env["res.users.apikeys"].sudo().search(
            [("user_id", "=", user.id)], order="id desc", limit=1
        ).write({"x_role_id": role.id})
        role.invalidate_recordset()
        self.assertEqual(role.x_apikey_count, 1)
        action = role.action_mcp_show_apikeys()
        self.assertEqual(action["domain"], [("x_role_id", "in", [role.id])])
        action = role.show_role_user_ids()
        self.assertEqual(action["domain"], [("id", "in", [user.id])])

    # -- API-key wizard and ready form ---------------------------------------

    def test_apikey_wizard_is_plain(self):
        tree = self._arch("res.users.apikeys.description", "base.form_res_users_key_description")
        self.assertFalse(tree.xpath("//div[hasclass('alert')]"), "no tip banner")
        self.assertFalse(tree.xpath("//a[starts-with(@href, 'http')]"), "no external links")
        role = tree.xpath("//field[@name='x_role_id']")
        self.assertEqual(len(role), 1)
        self.assertEqual(role[0].get("placeholder"), "No role, same rights as you")
        self.assertTrue(role[0].get("help"))
        name = tree.xpath("//field[@name='name']")[0]
        self.assertTrue(name.get("help"))

    def test_apikey_ready_form_names_the_rights(self):
        tree = self._arch("res.users.apikeys.show", "base.form_res_users_key_show")
        self.assertTrue(tree.xpath("//field[@name='x_role_id']"))
        warnings = tree.xpath("//p[hasclass('alert-warning')]")
        self.assertEqual(len(warnings), 1)
        self.assertNotIn("full access", etree.tostring(warnings[0], encoding="unicode"))

    # -- unchanged on purpose -----------------------------------------------

    def test_create_from_user_wizard_does_not_assign(self):
        """ "Create role from user" reads the groups; assigning is done on the user."""
        self.assertNotIn("assign_to_user", self.env["wizard.create.role.from.user"]._fields)
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
        self.assertFalse(user.role_line_ids)
