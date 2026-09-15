"""Does a role-bound API key actually narrow anything?

Every other test in this suite calls our own methods and asserts on their
return values. That is how the 17.0 branch could sit at "0 failed of 72"
while scoped API keys did nothing at all on Odoo 17: the module's methods
were fine, but nothing in Odoo 17 ever called them.

So these tests go the other way round. They set up a narrowed request and
then ask *Odoo* the questions Odoo asks itself during a real RPC call:
which models may I touch, am I in this group, which record rules apply.
Anything that regresses the wiring between our overrides and core's
permission machinery fails here, on every supported version.
"""

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from .. import compat
from ..models.res_users_apikeys import (
    clear_thread_api_key_role_id,
    set_thread_api_key_role_id,
)


class TestRoleNarrowing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_system = cls.env.ref("base.group_system")
        # A deliberately small role: plain internal user, nothing else.
        cls.role = cls.env["res.users.role"].create(
            {
                "name": "MCP Narrowing Test Role",
                "implied_ids": [(6, 0, [cls.group_user.id])],
            }
        )
        # The key owner is an administrator — the exact case the customer
        # reported, where the key kept full rights despite the role.
        # Deliberately no `role_line_ids`: base_user_role would then sync
        # the user's groups down to the role and there would be nothing
        # left to narrow, which is the opposite of what we want to prove.
        cls.user = cls.env["res.users"].create(
            {
                "name": "MCP Narrowing Owner",
                "login": "mcp_narrowing_owner",
                compat.USER_GROUPS_FIELD: [(6, 0, [cls.group_user.id, cls.group_system.id])],
            }
        )

    def setUp(self):
        super().setUp()
        self.addCleanup(clear_thread_api_key_role_id)
        self.addCleanup(self.env.registry.clear_cache)

    def _narrowed_env(self):
        """An env for the key owner with the role active, as during an RPC."""
        set_thread_api_key_role_id(self.role.id)
        self.env.registry.clear_cache()
        return self.env(user=self.user)

    def _plain_env(self):
        clear_thread_api_key_role_id()
        self.env.registry.clear_cache()
        return self.env(user=self.user)

    def test_role_is_picked_up(self):
        self.assertEqual(self._narrowed_env().user._get_api_key_role(), self.role)
        self.assertFalse(self._plain_env().user._get_api_key_role())

    def test_group_ids_are_the_role_closure(self):
        narrowed = set(self._narrowed_env().user._get_group_ids())
        self.assertIn(self.group_user.id, narrowed)
        self.assertNotIn(
            self.group_system.id,
            narrowed,
            "the key owner's own admin group leaked into the narrowed group set",
        )

    def test_has_group_answers_for_the_role(self):
        """`has_group` is what most `groups=` checks in Odoo end up calling."""
        self.assertTrue(self._plain_env().user.has_group("base.group_system"))
        self.assertFalse(
            self._narrowed_env().user.has_group("base.group_system"),
            "an admin key bound to a plain-user role still reports as system admin",
        )

    def test_acl_narrows_model_access(self):
        """The gate that decides whether a model is reachable at all."""
        Access = self._plain_env()["ir.model.access"]
        self.assertIn("ir.model.access", Access._get_allowed_models("write"))

        Access = self._narrowed_env()["ir.model.access"]
        self.assertNotIn(
            "ir.model.access",
            Access._get_allowed_models("write"),
            "role-bound key can still write ACL rows",
        )
        with self.assertRaises(AccessError):
            Access.check("ir.model.access", "write")

    def _hide_from(self, group, partner):
        """A record rule that hides `partner` from members of `group`."""
        self.env["ir.rule"].create(
            {
                "name": f"MCP test rule — {group.name}",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "groups": [(6, 0, [group.id])],
                "domain_force": f"[('id', '!=', {partner.id})]",
                "perm_read": True,
            }
        )

    def _can_see(self, env, partner):
        """Assert through a real search, not by reading the domain back.

        Odoo 19 normalises `('id', '!=', x)` into `('id', 'not in', [x])`,
        so comparing domain terms is version-specific. What the operator
        cares about is whether the row comes back.
        """
        return bool(env["res.partner"].search([("id", "=", partner.id)]))

    def test_record_rules_follow_the_role_not_the_user(self):
        """Record rules decide which rows come back, so they have to be
        intersected with the role's groups. Odoo 17 and 18 read the user's
        own groups here, which is the half of narrowing that silently did
        nothing."""
        partner = self.env["res.partner"].create({"name": "MCP rule probe"})
        self._hide_from(self.group_system, partner)

        self.assertFalse(
            self._can_see(self._plain_env(), partner),
            "baseline: the admin-group rule should hide this row",
        )
        self.assertTrue(
            self._can_see(self._narrowed_env(), partner),
            "a rule for a group outside the role was applied as if the key "
            "still carried that group",
        )

    def test_record_rules_for_the_role_still_apply(self):
        """The mirror image: narrowing must not throw every rule away."""
        partner = self.env["res.partner"].create({"name": "MCP rule probe 2"})
        self._hide_from(self.group_user, partner)

        self.assertFalse(
            self._can_see(self._narrowed_env(), partner),
            "a rule for a group the role does carry was dropped",
        )

    def test_narrowing_does_not_leak_into_the_next_request(self):
        """Workers are reused. A UI session following an API call on the
        same thread must see the user's real rights."""
        self.assertFalse(self._narrowed_env().user.has_group("base.group_system"))
        self.assertTrue(self._plain_env().user.has_group("base.group_system"))
