from odoo.tests import HttpCase, tagged

from .. import compat


@tagged("post_install", "-at_install")
class TestGovernanceSmokeTour(HttpCase):
    """Smoke-level UI tour for the MCP Pro app.

    Mirrors what an Odoo App Store reviewer sees on a freshly installed
    DB: open the app, navigate the menus, confirm the empty-state pages
    render. If this test passes from a clean install, the listing
    survives basic review.
    """

    def test_smoke_tour(self):
        # The web client moved from /web to /odoo in Odoo 18.
        self.start_tour(
            "/odoo" if compat.ODOO_VERSION >= 18 else "/web",
            "pan_mcp_pro_governance.smoke",
            login="admin",
        )
