from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestGovernanceSmokeTour(HttpCase):
    """Smoke-level UI tour for the MCP Pro app.

    Mirrors what an Odoo App Store reviewer sees on a freshly installed
    DB: open the app, navigate the menus, confirm the empty-state pages
    render. If this test passes from a clean install, the listing
    survives basic review.
    """

    def test_smoke_tour(self):
        self.start_tour(
            "/odoo",
            "pan_mcp_pro_governance.smoke",
            login="admin",
        )
