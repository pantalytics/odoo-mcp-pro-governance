"""Collapse Access Rights to a single MCP Pro dropdown (No / Administrator).

The v0.x layout exposed two MCP Pro groups: ``User`` and ``Manager``.
v0.5 collapsed them to a single ``Administrator`` group; users now
either have it (full MCP Pro admin) or do not (regular internal user,
no MCP Pro UI). The ``Administrator`` group keeps the existing xmlid
``group_mcp_governance_manager`` so users who already had it stay
administrators on upgrade.

We unlink the obsolete ``group_mcp_governance_user``. Users who only
held that group keep all their other groups — every internal user
already has ``base.group_user``, which is what gives them backend
access; the dropped group only governed visibility of the MCP Pro
sub-menus, which they no longer need.

Why explicit reference cleanup is needed:
ACL rows whose xmlid was removed in newer versions of
``security/ir.model.access.csv`` are not yet cleaned up at this point
in the upgrade — Odoo deletes stale module-data records *after*
post-migrations run. We therefore see them in ``ir_model_access`` with
a FK pointing at the group we are about to delete, and the unlink
fails with ``ForeignKeyViolation``. Same risk for ``ir.rule`` group
links via ``rule_group_rel``. Clean both before unlinking.
"""

from odoo.api import SUPERUSER_ID, Environment


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})

    old_user_group = env.ref(
        "pan_mcp_pro_governance.group_mcp_governance_user",
        raise_if_not_found=False,
    )
    if not old_user_group:
        return

    group_id = old_user_group.id

    # ir.model.access rows pointing at the dropped group: stale ones
    # whose xmlid is no longer in security/ir.model.access.csv but
    # which still exist in the DB at this stage of the upgrade.
    env["ir.model.access"].search([("group_id", "=", group_id)]).unlink()

    # ir.rule rows linked to the group via the M2M `rule_group_rel`.
    # We delete the link, not the rule — rules may still be needed
    # by other groups. Raw SQL because there is no ORM-level way to
    # detach one side of a M2M without loading both sides.
    cr.execute(
        "DELETE FROM rule_group_rel WHERE group_id = %s",
        (group_id,),
    )

    old_user_group.unlink()
