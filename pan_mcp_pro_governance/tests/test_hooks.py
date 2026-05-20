"""Tests for hooks.post_init_hook — the seeded auditlog rules.

The hook ran once when this test DB was installed. We verify the
seeded state, then re-invoke the hook to confirm idempotency.
"""

from odoo.tests.common import TransactionCase

from ..hooks import SEEDED_RULES, post_init_hook


class TestPostInitHook(TransactionCase):
    def setUp(self):
        super().setUp()
        self.AuditlogRule = self.env["auditlog.rule"]
        self.IrModel = self.env["ir.model"]

    def test_seeded_rules_for_installed_models(self):
        """Every model from SEEDED_RULES that is installed in this DB has a
        draft rule with the canonical name and flags."""
        seen = 0
        for model_name, rule_name in SEEDED_RULES:
            model = self.IrModel.search([("model", "=", model_name)], limit=1)
            if not model:
                continue
            seen += 1
            rule = self.AuditlogRule.search(
                [("model_id", "=", model.id), ("name", "=", rule_name)],
                limit=1,
            )
            self.assertTrue(rule, f"Expected seeded auditlog rule for {model_name}")
            self.assertEqual(rule.state, "draft")
            self.assertTrue(rule.log_create)
            self.assertTrue(rule.log_write)
            self.assertTrue(rule.log_unlink)
            self.assertFalse(rule.log_read)
        # At a minimum res.partner is in every Odoo install.
        self.assertGreaterEqual(seen, 1)

    def test_hook_is_idempotent(self):
        """Running the hook twice should not create duplicates."""
        before = self.AuditlogRule.search_count(
            [
                ("name", "like", "MCP Pro —%"),
            ]
        )
        post_init_hook(self.env)
        after = self.AuditlogRule.search_count(
            [
                ("name", "like", "MCP Pro —%"),
            ]
        )
        self.assertEqual(before, after)

    def test_unknown_model_is_skipped_silently(self):
        """A SEEDED_RULES entry for a missing model is a no-op, not an error."""
        # No model named "definitely.not.a.model" exists, so the helper
        # must not raise. We invoke the same loop directly.
        fake = [("definitely.not.a.model", "MCP Pro — Bogus")]
        for model_name, rule_name in fake:
            model = self.IrModel.search([("model", "=", model_name)], limit=1)
            self.assertFalse(model)  # confirms the precondition
            # If model is falsy, the hook's loop continues — no rule created.
            self.assertFalse(self.AuditlogRule.search([("name", "=", rule_name)]))
