"""Regression for #28 — revoking an API key must not break the audit log.

``res.users.apikeys`` is declared ``_auto = False`` and its table is built
by hand, so Odoo never creates a foreign key for
``auditlog.http.request.x_api_key_id``. No ``ondelete`` rule can fire, and
core's ``_remove()`` drops the key with a raw ``DELETE``: the many2one is
left pointing at a row that is gone, and anything that renders it raises
``MissingError`` ("Record does not exist or has been deleted").

The fix is a snapshot of the key identity — ``x_api_key_ref`` (id) and
``x_api_key_name`` (description) — written in ``create`` next to the
many2one, and shown by the views in place of it.
"""

import datetime
from unittest import mock

from odoo.exceptions import MissingError
from odoo.tests.common import TransactionCase

from .. import compat
from ..models import auditlog_http_request as audit_http_request


class TestAuditKeySnapshot(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ApiKey = cls.env["res.users.apikeys"].sudo()
        cls.Request = cls.env["auditlog.http.request"]
        # A key owner with zero groups trips a latent core bug in
        # res.users._check_expiration_date during key generation; every
        # real internal user carries group_user. See tests/test_apikeys.py.
        cls.user = cls.env["res.users"].create(
            {
                "name": "MCP Snapshot Owner",
                "login": "mcp_snapshot_owner",
                compat.USER_GROUPS_FIELD: [(4, cls.env.ref("base.group_user").id)],
            }
        )

    def _make_key(self, name):
        """Generate one key for self.user through the canonical entry point."""
        api = self.ApiKey.with_user(self.user)
        if compat.ODOO_VERSION >= 18:
            # Odoo 18 added the expiration_date argument to _generate.
            future = datetime.datetime.now() + datetime.timedelta(days=1)
            api._generate("rpc", name, future)
        else:
            api._generate("rpc", name)
        return self.ApiKey.search(
            [("user_id", "=", self.user.id), ("name", "=", name)],
            order="id desc",
            limit=1,
        )

    def _log_request(self, key):
        """Create an audit row as if the in-flight request used ``key``."""
        with mock.patch.object(
            audit_http_request,
            "current_request_api_key_id",
            return_value=key.id,
        ):
            return self.Request.create(
                {
                    "name": "/json/2/sale.order/search_read",
                    "root_url": "http://localhost:8069/",
                    "user_id": self.user.id,
                }
            )

    def _revoke(self, key_id):
        """Delete the key row the way core's ``_remove()`` does."""
        self.env.cr.execute("DELETE FROM res_users_apikeys WHERE id = %s", (key_id,))
        self.env.registry.clear_cache()
        self.env.invalidate_all()

    def test_create_snapshots_key_identity(self):
        key = self._make_key("claude desktop")
        req = self._log_request(key)
        self.assertEqual(req.x_api_key_id, key)
        self.assertEqual(req.x_api_key_ref, key.id)
        self.assertEqual(req.x_api_key_name, "claude desktop")

    def test_no_key_leaves_snapshot_empty(self):
        with mock.patch.object(
            audit_http_request,
            "current_request_api_key_id",
            return_value=None,
        ):
            req = self.Request.create({"name": "/web/dataset/call_kw/res.partner/read"})
        self.assertFalse(req.x_api_key_id)
        self.assertFalse(req.x_api_key_ref)
        self.assertFalse(req.x_api_key_name)

    def test_audit_row_survives_key_revocation(self):
        key = self._make_key("n8n automation")
        key_id = key.id
        req = self._log_request(key)

        self._revoke(key_id)
        self.assertFalse(self.ApiKey.browse(key_id).exists())

        # The many2one now dangles — this is the reported crash.
        self.assertEqual(req.x_api_key_id.id, key_id)
        with self.assertRaises(MissingError):
            req.x_api_key_id.read(["name"])

        # ...but the row still reads, and the key identity is still there.
        self.assertEqual(req.x_api_key_ref, key_id)
        self.assertEqual(req.x_api_key_name, "n8n automation")

        # Rendering the columns the list view asks for must not raise.
        data = req.read(
            [
                "create_date",
                "x_model",
                "x_method",
                "user_id",
                "x_api_key_name",
                "x_api_key_ref",
                "name",
                "http_session_id",
            ]
        )[0]
        self.assertEqual(data["x_api_key_name"], "n8n automation")
        self.assertEqual(data["x_api_key_ref"], key_id)

        # Same for grouping the log by key, the documented workflow.
        groups = self.Request._read_group([("id", "=", req.id)], ["x_api_key_name"])
        self.assertEqual(groups[0][0], "n8n automation")

    def test_views_show_the_snapshot_not_the_many2one(self):
        """No view may render x_api_key_id — that is what raises after #28."""
        # auditlog.log carries the same field as a related, is rendered in
        # the per-record Logs views, and crashed the same way -- the reporter
        # had to clean auditlog_log rows by hand too.
        for model, xmlid, view_type in (
            ("auditlog.http.request", "pan_mcp_auditlog.view_auditlog_http_request_tree", "list"),
            ("auditlog.http.request", "pan_mcp_auditlog.view_auditlog_http_request_form", "form"),
            (
                "auditlog.http.request",
                "pan_mcp_auditlog.view_auditlog_http_request_search",
                "search",
            ),
            ("auditlog.log", "pan_mcp_auditlog.view_auditlog_log_tree", "list"),
            ("auditlog.log", "pan_mcp_auditlog.view_auditlog_log_form", "form"),
            ("auditlog.log", "pan_mcp_auditlog.view_auditlog_log_search", "search"),
        ):
            with self.subTest(view=xmlid):
                arch = self.env[model].get_view(self.env.ref(xmlid).id, view_type)["arch"]
                self.assertNotIn(
                    'name="x_api_key_id"',
                    arch,
                    f"{view_type} view still renders the dangling many2one",
                )
                self.assertNotIn("'group_by':'x_api_key_id'", arch)
                self.assertIn("x_api_key_name", arch)
