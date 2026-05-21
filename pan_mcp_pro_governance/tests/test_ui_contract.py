"""UI-contract tests — the design rules from docs/dev/design.md, as code.

These tests guard structural design decisions that are easy to break
accidentally (adding a second top-level menu, exposing Configuration
to non-managers). If these fail, read docs/dev/design.md before fixing —
the test exists because the design says so.
"""

from odoo.tests.common import TransactionCase


class TestMenuContract(TransactionCase):
    """Progressive disclosure: one app, manager-only Configuration."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.IrUiMenu = cls.env["ir.ui.menu"].sudo()
        cls.IrModelData = cls.env["ir.model.data"].sudo()

    def _menu(self, xmlid):
        return self.env.ref(f"pan_mcp_pro_governance.{xmlid}")

    def test_exactly_one_top_level_menu(self):
        """docs/dev/design.md: 'Eén top-level app: MCP Pro. Geen tweede.'"""
        own_menu_data = self.IrModelData.search(
            [
                ("module", "=", "pan_mcp_pro_governance"),
                ("model", "=", "ir.ui.menu"),
            ]
        )
        top_level_xmlids = []
        for row in own_menu_data:
            menu = self.IrUiMenu.browse(row.res_id)
            if menu.exists() and not menu.parent_id:
                top_level_xmlids.append(row.name)
        self.assertEqual(
            top_level_xmlids,
            ["menu_mcp_governance_root"],
            f"Expected one top-level menu, found {top_level_xmlids}. See docs/dev/design.md.",
        )

    def test_root_menu_named_mcp_pro(self):
        """The App Store listing name is 'MCP Pro' — the menu must match."""
        self.assertEqual(self._menu("menu_mcp_governance_root").name, "MCP Pro")

    def test_configuration_is_manager_only(self):
        """docs/dev/design.md: Configuration is for managers, not users."""
        config = self._menu("menu_mcp_governance_config")
        manager_group = self.env.ref("pan_mcp_pro_governance.group_mcp_governance_manager")
        self.assertIn(
            manager_group,
            config.group_ids,
            "Configuration menu must be gated to the Manager group.",
        )

    def test_root_menu_visible_to_internal_users(self):
        """Any internal user can see the MCP Pro menu (they manage their own API keys)."""
        root = self._menu("menu_mcp_governance_root")
        internal_user_group = self.env.ref("base.group_user")
        self.assertIn(internal_user_group, root.group_ids)
