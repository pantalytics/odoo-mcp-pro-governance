# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class AuditLogRuleCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.models = set()

    @classmethod
    def create_rule(cls, vals):
        rule = cls.env["auditlog.rule"].with_context(tracking_disable=True).create(vals)
        # Keep track of patched models
        cls.models |= set(rule.model_id.mapped("model"))
        return rule

    # Odoo 18's test framework asserts, after every test, that no extra
    # attributes were left on any model class (v19 has no such check). OCA
    # auditlog patches the model class (class-level, NOT transactional) when a
    # rule is confirmed; under TransactionCase the DB rule.state is restored by
    # the per-test savepoint rollback but the Python patches are not. So we
    # manage the patches by hand around each test: re-apply on setUp (for rules
    # the DB still reports confirmed, e.g. from setUpClass) and strip on
    # tearDown (before the framework check). Both are no-ops on 19, where the
    # check does not exist and rules are reverted only at tearDownClass.
    def setUp(self):
        super().setUp()
        self.env["auditlog.rule"].search([("state", "=", "confirmed")])._register_hook()

    def tearDown(self):
        for rule in self.env["auditlog.rule"].search([("state", "=", "confirmed")]):
            try:
                rule._revert_methods()
            except KeyError:  # pragma: no cover
                continue  # Model not loaded yet
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        for rule in cls.env["auditlog.rule"].search([]):
            try:
                rule.set_to_draft()
            except KeyError:  # pragma: no cover
                continue  # Model not loaded yet

        # Assert no patched methods remain
        for model in cls.models:
            for method in ["create", "read", "write", "unlink"]:
                assert not hasattr(getattr(cls.env[model], method), "origin"), (
                    f"{model} {method} still patched"
                )
        super().tearDownClass()
