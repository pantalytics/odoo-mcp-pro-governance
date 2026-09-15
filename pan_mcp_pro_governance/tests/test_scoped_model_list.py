"""The MCP `list_models` tool must mirror the API-key role.

`list_models` on the server reads `ir.model`. A scoped read-only role holds
none of the technical-model groups, so on its own it either sees nothing
(ACL denies ir.model) or -- if granted ir.model read naively -- the whole
catalogue it cannot actually read. This module grants the read and scopes the
rows to the role's own models. These tests drive that end to end without an
HTTP request by seeding the role thread-local the same way `_check_credentials`
does at runtime.
"""

from odoo.tests.common import TransactionCase

from ..models.res_users_apikeys import (
    clear_thread_api_key_role_id,
    set_thread_api_key_role_id,
)


class TestScopedModelList(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        IrModel = cls.env["ir.model"]
        # A group that grants read on res.partner only -- and, crucially, is
        # NOT base.group_user, so it carries no ir.model access. This mimics a
        # scoped read-only MCP role.
        cls.scoped_group = cls.env["res.groups"].create({"name": "MCP Scoped Test"})
        cls.env["ir.model.access"].create(
            {
                "name": "mcp scoped: read res.partner",
                "model_id": IrModel._get_id("res.partner"),
                "group_id": cls.scoped_group.id,
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
        )
        cls.role = cls.env["res.users.role"].create(
            {
                "name": "MCP Scoped Role",
                "implied_ids": [(6, 0, [cls.scoped_group.id])],
            }
        )
        # The owning user is a normal internal user (base.group_user). The role
        # narrowing is what scopes the request -- proving the scoping rides on
        # the active role, not on the user's own groups.
        cls.user = cls.env["res.users"].create(
            {
                "name": "MCP Scoped User",
                "login": "mcp_scoped_user",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, cls.scoped_group.id])],
            }
        )

    def tearDown(self):
        # Never let a seeded role leak into another test on this worker.
        clear_thread_api_key_role_id()
        super().tearDown()

    def _as_role(self):
        set_thread_api_key_role_id(self.role.id)

    def test_ir_model_is_readable_for_scoped_role(self):
        self._as_role()
        allowed = self.env["ir.model.access"].with_user(self.user)._get_allowed_models("read")
        self.assertIn("res.partner", allowed)
        # Injected so the ACL check on ir.model passes for list_models...
        self.assertIn("ir.model", allowed)
        # ...but the role still cannot read unrelated technical models.
        self.assertNotIn("ir.rule", allowed)

    def test_ir_model_rows_are_scoped_to_the_role(self):
        self._as_role()
        names = set(
            self.env["ir.model"]
            .with_user(self.user)
            .search([("transient", "=", False)])
            .mapped("model")
        )
        self.assertIn("res.partner", names)
        # A model the role cannot read must not appear in the catalogue.
        self.assertNotIn("ir.rule", names)
        # ir.model is granted for the ACL check only; it is noise in the model
        # list, so the row rule hides it.
        self.assertNotIn("ir.model", names)

    def test_no_role_leaves_catalogue_untouched(self):
        # A non-role request that is otherwise allowed to read ir.model must be
        # untouched by the global rule. Admin (base.group_system) can read the
        # catalogue and, being a non-superuser, still has record rules applied,
        # so it proves the rule resolves to an always-true clause off-role.
        clear_thread_api_key_role_id()
        admin = self.env.ref("base.user_admin")
        count = self.env["ir.model"].with_user(admin).search_count([("transient", "=", False)])
        self.assertGreater(count, 50)

    def test_write_is_never_granted_on_ir_model(self):
        # The introspection grant is read-only: ir.model must not leak into the
        # role's writable set.
        self._as_role()
        allowed_write = (
            self.env["ir.model.access"].with_user(self.user)._get_allowed_models("write")
        )
        self.assertNotIn("ir.model", allowed_write)
