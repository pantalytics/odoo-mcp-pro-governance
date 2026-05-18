"""Auto-suspend API keys that have no role on upgrade to v0.3.

v0.3 requires every API key to be bound to an OCA `res.users.role`. Pre-v0.3
keys have no role. We suspend them on install so they cannot authenticate
until an admin re-creates them with a role attached.

This is intentional: "kneiter strak", no silent fallback to full user rights.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE res_users_apikeys "
        "SET x_state = 'suspended' "
        "WHERE x_role_id IS NULL AND COALESCE(x_state, 'active') = 'active' "
        "RETURNING id"
    )
    suspended = cr.fetchall()
    if suspended:
        _logger.warning(
            "MCP Pro Governance 19.0.0.3.0: auto-suspended %d API key(s) "
            "without a role. IDs: %s. Recreate them via the wizard with a "
            "role attached to restore access.",
            len(suspended),
            [row[0] for row in suspended],
        )
    else:
        _logger.info(
            "MCP Pro Governance 19.0.0.3.0: no role-less API keys found, "
            "nothing to suspend."
        )
