"""Add admin to MCP Pro Manager group for existing installs.

Versions <= 1.3.0 relied on `user_ids` on res.groups to grant admin
access to the MCP Pro menu, which silently failed on fresh installs and
left admin without the group (and thus without the menu) on existing
databases. Fix it once on upgrade.
"""

from odoo.addons.pan_mcp_pro_governance.hooks import ensure_admin_in_manager_group
from odoo.api import SUPERUSER_ID, Environment


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})
    ensure_admin_in_manager_group(env)
