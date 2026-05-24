# Copyright 2026 Opener B.V. <https://opener.amsterdam>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError

from odoo.addons.base.tests.common import BaseCommon


class TestModelAuditlogRule(BaseCommon):
    def test_model_required(self):
        """Model is required, but not as a field property."""
        model_id = self.env.ref("base.model_res_groups").id
        # Test create
        with self.assertRaisesRegex(
            UserError,
            "No model defined to create line",
        ):
            with self.env.cr.savepoint():
                self.env["auditlog.rule"].create(
                    {
                        "name": "Test rule",
                    },
                )
        rule = self.env["auditlog.rule"].create(
            {
                "name": "Test rule",
                "model_id": model_id,
            },
        )
        # Test write
        with self.assertRaisesRegex(
            UserError,
            "'model_id' cannot be empty",
        ):
            with self.env.cr.savepoint():
                rule.model_id = False

    def test_revert_methods_marker_missing(self):
        """Reverting a confirmed rule must not crash if the marker attribute
        was dropped from the dynamic model class (e.g. after a registry rebuild)
        while the patched method itself still carries its ``.origin``.
        Regression: AttributeError on delattr in _revert_methods.
        """
        model_id = self.env.ref("base.model_res_groups").id
        rule = self.env["auditlog.rule"].create(
            {"name": "Marker drop", "model_id": model_id, "log_write": True}
        )
        rule.set_to_confirmed()
        groups_cls = type(self.env["res.groups"])
        self.assertTrue(hasattr(groups_cls.write, "origin"))
        self.assertIn("auditlog_ruled_write", groups_cls.__dict__)
        # Simulate the out-of-sync state: marker gone, patched method stays.
        delattr(groups_cls, "auditlog_ruled_write")
        # Without the guard this raises AttributeError.
        rule.set_to_draft()
        self.assertFalse(hasattr(groups_cls.write, "origin"))
