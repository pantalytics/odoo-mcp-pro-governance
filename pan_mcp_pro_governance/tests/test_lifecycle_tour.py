"""Drives the full agent-identity state machine through the UI."""

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestLifecycleTour(HttpCase):
    """End-to-end check that the lifecycle buttons behave per docs/dev/design.md:
    draft → active → suspended → active → revoked, with the right buttons
    visible in each state (progressive disclosure of actions)."""

    def test_lifecycle_tour(self):
        self.start_tour(
            "/odoo",
            "pan_mcp_pro_governance.lifecycle",
            login="admin",
        )
