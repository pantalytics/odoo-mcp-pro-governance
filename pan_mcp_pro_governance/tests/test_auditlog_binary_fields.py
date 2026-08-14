"""Tests for the binary-field exclusion in ``get_auditlog_fields``.

A ``log_type = full`` rule snapshots every audited field of the record.
For an attachment-backed Binary field that snapshot is not a column
read: ``Binary.read`` resolves the value through
``ir.attachment.search_fetch``, and a search flushes ``ir.attachment``.
When the transaction still carries a deferred write on that model the
flush raises ``AssertionError: Could not find all values of
ir.attachment(N,) to flush them`` and the whole transaction rolls back
— reported from production on Odoo 19 when confirming a sales order
that creates a project (with a document folder) and a delivery at once.

The rule's own ``fields_to_exclude_ids`` cannot prevent this: it is
applied in ``create_logs``, long after the values have been read. The
exclusion has to happen in the field list itself.
"""

from odoo.tests.common import TransactionCase

# Smallest valid PNG: 1x1 transparent pixel, base64-encoded as the ORM
# expects for an Image field.
ONE_PIXEL_PNG = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    b"YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class TestAuditlogBinaryFields(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Rule = cls.env["auditlog.rule"]
        cls.partner_model = cls.env.ref("base.model_res_partner")

    def test_binary_fields_are_not_audited(self):
        """``res.partner.image_1920`` is a ``fields.Image``, so
        attachment-backed. It must not appear in the audited set, while
        ordinary columns still do."""
        fields_list = self.Rule.get_auditlog_fields(self.env["res.partner"])

        self.assertNotIn("image_1920", fields_list)
        self.assertIn("name", fields_list)
        self.assertIn("email", fields_list)

    def test_no_binary_field_survives_the_filter(self):
        """Guard the whole model rather than one field name: no audited
        field of ``res.partner`` may be of type ``binary``."""
        model = self.env["res.partner"]
        audited = self.Rule.get_auditlog_fields(model)

        binary_audited = [n for n in audited if model._fields[n].type == "binary"]
        self.assertFalse(
            binary_audited,
            f"binary fields leaked into the audited set: {binary_audited}",
        )

    def test_full_log_create_with_an_image_logs_without_the_binary(self):
        """End-to-end: a confirmed full-log rule must log the create of a
        record carrying an image, and the log must not contain the image
        fields."""
        # `auditlog.rule` carries a unique constraint on `model_id`, and
        # `post_init_hook` already seeds a draft rule for `res.partner`.
        # Reuse it when present instead of creating a second one; the
        # TransactionCase rollback restores its original values.
        vals = {
            "log_type": "full",
            "log_create": True,
            "log_write": False,
            "log_unlink": False,
            "log_read": False,
            "log_export_data": False,
        }
        rule = self.Rule.search([("model_id", "=", self.partner_model.id)], limit=1)
        if rule:
            rule.write(vals)
        else:
            rule = self.Rule.create(
                dict(vals, name="Binary field test", model_id=self.partner_model.id)
            )
        rule.set_to_confirmed()
        self.addCleanup(rule.set_to_draft)

        partner = self.env["res.partner"].create(
            {"name": "Binary Audit Partner", "image_1920": ONE_PIXEL_PNG}
        )

        log = self.env["auditlog.log"].search(
            [
                ("model_id", "=", self.partner_model.id),
                ("res_id", "=", partner.id),
                ("method", "=", "create"),
            ],
            limit=1,
        )
        self.assertTrue(log, "full-log rule produced no create log")

        logged_fields = log.line_ids.mapped("field_name")
        self.assertIn("name", logged_fields)
        self.assertNotIn("image_1920", logged_fields)

        binary_logged = [
            n for n in logged_fields if self.env["res.partner"]._fields[n].type == "binary"
        ]
        self.assertFalse(
            binary_logged,
            f"binary field contents written to the audit log: {binary_logged}",
        )
