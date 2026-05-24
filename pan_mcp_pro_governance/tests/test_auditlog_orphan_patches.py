"""Tests for the orphan-patch cleanup in ``auditlog.rule._register_hook``.

OCA auditlog monkey-patches ``type(model).{create,read,write,unlink,
export_data}`` when a rule transitions to ``state='confirmed'`` and
reverts the patch on ``set_to_draft``/``unlink``. The revert only runs
on the worker that processed the state change; other workers (notably
the long-running Odoo SaaS cron worker) rely on the
``registry_invalidated`` signal to reload their registry, and in
practice that signal does not always reach every process. The result
is a class that keeps the patched method indefinitely, producing audit
log rows for a model that has no rule.

The fix lives in ``pan_mcp_auditlog`` — ``_register_hook`` now scrubs
markers without a matching confirmed rule on every registry build.
"""

from odoo.tests.common import TransactionCase


class TestAuditlogOrphanPatches(TransactionCase):
    def test_register_hook_reverts_orphan_patches(self):
        """Reproduces the production incident: a rule that was confirmed
        and then flipped to draft via a side channel (here: direct SQL,
        in production: a worker that missed the registry_invalidated
        signal) leaves its patches on the model class. The next
        ``_register_hook`` pass — run on every registry build — must
        strip them.
        """
        rule = self.env["auditlog.rule"].create(
            {
                "name": "Orphan patch test",
                "model_id": self.env.ref("base.model_res_groups").id,
                "log_write": True,
                "log_create": False,
                "log_unlink": False,
                "log_read": False,
                "log_export_data": False,
            },
        )
        rule.set_to_confirmed()
        groups_cls = type(self.env["res.groups"])
        self.assertIn("auditlog_ruled_write", groups_cls.__dict__)
        self.assertTrue(hasattr(groups_cls.write, "origin"))

        # Bypass write() (which would call _revert_methods) to mimic the
        # cross-worker broken state.
        self.env.cr.execute(
            "UPDATE auditlog_rule SET state = 'draft' WHERE id = %s",
            (rule.id,),
        )
        rule.invalidate_recordset(["state"])
        self.assertEqual(rule.state, "draft")
        self.assertIn("auditlog_ruled_write", groups_cls.__dict__)

        self.env["auditlog.rule"]._register_hook()

        self.assertNotIn("auditlog_ruled_write", groups_cls.__dict__)
        self.assertFalse(hasattr(groups_cls.write, "origin"))

    def test_register_hook_keeps_active_patches(self):
        """Sanity check: a still-confirmed rule must NOT be stripped by
        the orphan-cleanup pass.
        """
        rule = self.env["auditlog.rule"].create(
            {
                "name": "Active patch test",
                "model_id": self.env.ref("base.model_res_groups").id,
                "log_write": True,
                "log_create": False,
                "log_unlink": False,
                "log_read": False,
                "log_export_data": False,
            },
        )
        rule.set_to_confirmed()
        groups_cls = type(self.env["res.groups"])
        self.assertIn("auditlog_ruled_write", groups_cls.__dict__)

        self.env["auditlog.rule"]._register_hook()

        self.assertIn("auditlog_ruled_write", groups_cls.__dict__)
        self.assertTrue(hasattr(groups_cls.write, "origin"))

        rule.set_to_draft()
        self.assertNotIn("auditlog_ruled_write", groups_cls.__dict__)
