# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Cross-version helper for Odoo 17 / 18 / 19.

Odoo 19 introduced declarative ``models.Constraint`` (SQL constraints were
``_sql_constraints`` tuples on <= 18) and moved ``NewId`` into the
``odoo.orm`` package. This module exposes the running major version so the
fork can branch on it. See docs/dev/multi-version-port-plan.md.
"""

from odoo.release import version_info

ODOO_VERSION = version_info[0]

# res.users / ir.ui.menu groups M2M (renamed groups_id -> group_ids in 19).
# Used by the vendored tests.
USER_GROUPS_FIELD = "group_ids" if ODOO_VERSION >= 19 else "groups_id"
