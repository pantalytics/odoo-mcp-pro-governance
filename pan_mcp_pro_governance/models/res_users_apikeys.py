"""Bind each API key to one OCA `res.users.role`.

The key is still owned by one `res.users` (Odoo native, billing-bound) but
its capability surface is narrowed to the linked role for the duration of
any request that authenticates via this key. See ADR-010.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsersApikeys(models.Model):
    _inherit = "res.users.apikeys"

    def init(self):
        super().init()
        # The parent has _auto = False and manages its own schema. Add our
        # columns explicitly so they exist before any migration runs.
        self.env.cr.execute("""
            ALTER TABLE res_users_apikeys
            ADD COLUMN IF NOT EXISTS x_role_id integer,
            ADD COLUMN IF NOT EXISTS x_state varchar DEFAULT 'active',
            ADD COLUMN IF NOT EXISTS x_last_used timestamp without time zone,
            ADD COLUMN IF NOT EXISTS x_use_count integer DEFAULT 0
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS res_users_apikeys_x_role_id_idx
            ON res_users_apikeys (x_role_id)
        """)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS res_users_apikeys_x_state_idx
            ON res_users_apikeys (x_state)
        """)

    x_role_id = fields.Many2one(
        comodel_name="res.users.role",
        string="Role",
        ondelete="restrict",
        index=True,
        help="The OCA user role this key represents. The key's effective "
             "permissions during any request are exactly this role's groups — "
             "never broader than the owning user, and never broader than this role.",
    )
    x_state = fields.Selection(
        selection=[
            ("active", "Active"),
            ("suspended", "Suspended"),
            ("revoked", "Revoked"),
        ],
        default="active",
        required=True,
        index=True,
        string="State",
    )
    x_last_used = fields.Datetime(readonly=True, string="Last Used")
    x_use_count = fields.Integer(readonly=True, default=0, string="Use Count")

    @api.constrains("x_role_id", "user_id")
    def _check_role_belongs_to_user(self):
        for rec in self:
            if not rec.x_role_id:
                continue
            # base_user_role's role_ids compute is broken on 19.0; use the
            # underlying role_line_ids → role_id mapping directly.
            user_role_ids = rec.user_id.sudo().role_line_ids.mapped("role_id").ids
            if rec.x_role_id.id not in user_role_ids:
                raise ValidationError(
                    _("Role %(role)s is not assigned to user %(user)s. "
                      "Assign the role to the user first.",
                      role=rec.x_role_id.display_name, user=rec.user_id.login)
                )

    def _check_credentials(self, *, scope, key):
        """Override: stash matched key id + role id on the request session.

        Fails closed: if the key has a role but is suspended/revoked, deny.
        If anything goes wrong identifying the key, no attribution is recorded
        and Odoo's standard fallback (user's full rights) applies — which we
        consider acceptable only because the migration suspends pre-existing
        unscoped keys at install time.
        """
        user_id = super()._check_credentials(scope=scope, key=key)
        if not (user_id and request and key):
            return user_id

        try:
            index = key[:8]  # Odoo's INDEX_SIZE constant
            self.env.cr.execute(
                "SELECT id, x_role_id, x_state FROM res_users_apikeys "
                "WHERE user_id = %s AND index = %s",
                (user_id, index),
            )
            rows = self.env.cr.fetchall()
        except Exception:
            _logger.exception(
                "MCP Pro Governance: failed to resolve API key id; "
                "denying request to fail closed."
            )
            return None  # fail closed

        if len(rows) != 1:
            _logger.warning(
                "MCP Pro Governance: expected 1 matching key for "
                "user_id=%s index=%s, found %d. Denying request.",
                user_id, index, len(rows),
            )
            return None  # fail closed

        api_key_id, role_id, state = rows[0]

        if state != "active":
            _logger.warning(
                "MCP Pro Governance: API key id=%s is %s; denying request.",
                api_key_id, state,
            )
            return None  # fail closed

        request.session["x_mcp_api_key_id"] = api_key_id
        if role_id:
            request.session["x_mcp_api_key_role_id"] = role_id

        # Lightweight usage counter; one UPDATE per call. Tolerable for
        # the prototype — promote to a deferred / batched update if it
        # becomes a hot path.
        self.env.cr.execute(
            "UPDATE res_users_apikeys "
            "SET x_last_used = now() at time zone 'utc', "
            "    x_use_count = x_use_count + 1 "
            "WHERE id = %s",
            (api_key_id,),
        )
        return user_id
