"""Seed a default Administrator role for existing installs.

Fresh installs get the role via `post_init_hook`. Databases upgrading
from an earlier version run this migration instead. Idempotent: a role
is only created when zero roles exist in the database.
"""

from odoo.api import Environment, SUPERUSER_ID

from odoo.addons.pan_mcp_pro_governance.hooks import ensure_default_admin_role


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})
    ensure_default_admin_role(env)
