# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Cross-version helpers for Odoo 17 / 18 / 19.

Odoo 19 renamed the group fields this fork touches:
- ``res.users.groups_id``         -> ``res.users.group_ids``
- ``res.groups.trans_implied_ids`` -> ``res.groups.all_implied_ids``
and introduced ``res.groups.privilege`` / ``res.groups.privilege_id``
(absent on <= 18).

This mirrors pan_mcp_pro_governance/compat.py. It is duplicated here on
purpose: this module is a *dependency* of the governance addon, so it
cannot import from it. See docs/dev/multi-version-port-plan.md.
"""

from odoo.release import version_info

ODOO_VERSION = version_info[0]

USER_GROUPS_FIELD = "group_ids" if ODOO_VERSION >= 19 else "groups_id"
IMPLIED_FIELD = "all_implied_ids" if ODOO_VERSION >= 19 else "trans_implied_ids"


def user_groups(user):
    """Return the recordset of groups explicitly assigned to ``user``."""
    return user[USER_GROUPS_FIELD]


def implied_groups(groups):
    """Return the transitive closure of implied groups for ``groups``,
    *including the group(s) themselves* — matching Odoo 19's
    ``all_implied_ids`` semantics on every version.

    ``groups`` may be a ``res.groups`` recordset or a ``res.users.role`` (via
    ``_inherits``). On <= 18 ``trans_implied_ids`` excludes the group itself,
    so we add it back; the role->group sync relies on the self-inclusive set.
    """
    if ODOO_VERSION >= 19:
        return groups[IMPLIED_FIELD]
    base = groups.group_id if groups._name == "res.users.role" else groups
    return base | base.mapped(IMPLIED_FIELD)
