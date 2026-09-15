"""Direct tests for ``ir_http.current_request_api_key_id``.

This helper is the single source of truth for "which api key authenticates
the in-flight request", shared by ``auditlog.http.request.create`` and the
audit-rule scope filter. It must return the key id on the modern /json/2 +
browser path (request on the stack) and fall back to the ir.http._dispatch
snapshot on the legacy /jsonrpc + /xmlrpc paths (request popped by
borrow_request). Both consumers rely on that fallback, so lock it here.
"""

from unittest import mock

from odoo.tests.common import TransactionCase

from ..models import ir_http


class TestCurrentRequestApiKeyId(TransactionCase):
    def _bound_request(self, api_key_id):
        req = mock.MagicMock()
        req.session.get.return_value = api_key_id
        return mock.patch.object(ir_http, "http_request", req)

    def _no_request(self, snapshot):
        return mock.patch.multiple(
            ir_http,
            http_request=None,
            get_audit_request_snapshot=mock.Mock(return_value=snapshot),
        )

    def test_modern_path_returns_session_key(self):
        with self._bound_request(api_key_id=42):
            self.assertEqual(ir_http.current_request_api_key_id(), 42)

    def test_modern_path_without_key_returns_none(self):
        with self._bound_request(api_key_id=None):
            self.assertIsNone(ir_http.current_request_api_key_id())

    def test_legacy_path_falls_back_to_snapshot(self):
        with self._no_request(snapshot={"api_key_id": 7}):
            self.assertEqual(ir_http.current_request_api_key_id(), 7)

    def test_legacy_path_without_snapshot_returns_none(self):
        with self._no_request(snapshot=None):
            self.assertIsNone(ir_http.current_request_api_key_id())

    def test_legacy_path_snapshot_without_key_returns_none(self):
        with self._no_request(snapshot={"path": "/jsonrpc"}):
            self.assertIsNone(ir_http.current_request_api_key_id())
