"""Cross-version helpers for Odoo 17 / 18 / 19.

Odoo 19 reworked the group model and renamed several fields. This module
resolves the right name for the running Odoo version, so the rest of the
addon stays version-agnostic (see docs/dev/multi-version-port-plan.md).

What changed in 19:

- ``res.users.groups_id``        -> ``res.users.group_ids``
- ``res.groups.trans_implied_ids`` -> ``res.groups.all_implied_ids``
- ``res.users.all_group_ids`` + ``_compute_all_group_ids`` are new in 19
  (no equivalent exists on 18); guard any code that touches them with
  ``ODOO_VERSION >= 19``.
- ``res.groups.privilege`` model + ``privilege_id`` are new in 19; on 18
  groups carry ``category_id`` directly. This split is declarative, so it
  lives in version-specific data files, not here.

Field-name renames *can* be resolved at runtime — that is what this module
does. Declarative XML cannot, so the manifest's ``data`` list is the one
legitimate per-version difference between release branches.
"""

from odoo.release import version_info

ODOO_VERSION = version_info[0]

# res.users: the M2M of groups explicitly assigned to a user.
USER_GROUPS_FIELD = "group_ids" if ODOO_VERSION >= 19 else "groups_id"

# res.groups: the transitive closure of implied groups. On a res.users.role
# (which ``_inherits`` res.groups) this resolves through the delegation.
IMPLIED_FIELD = "all_implied_ids" if ODOO_VERSION >= 19 else "trans_implied_ids"


def user_groups(user):
    """Return the recordset of groups explicitly assigned to ``user``."""
    return user[USER_GROUPS_FIELD]


def implied_groups(groups):
    """Return the transitive closure of implied groups for ``groups``.

    ``groups`` may be a ``res.groups`` recordset or a ``res.users.role``
    (which exposes the field via ``_inherits``).
    """
    return groups[IMPLIED_FIELD]
