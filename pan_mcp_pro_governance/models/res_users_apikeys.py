"""Bind each API key to one OCA `res.users.role`.

The key is still owned by one `res.users` (Odoo native, billing-bound) but
its capability surface is narrowed to the linked role for the duration of
any request that authenticates via this key. See ADR-010.

Attribution storage: thread-local. The modern `/json/2/*` bearer auth path
keeps the request on the local stack, so `request.session` would have
worked there. But the legacy `/jsonrpc` path runs `dispatch_rpc()` inside
a `borrow_request()` context that pops the request — `request.session`
writes during that dispatch don't survive to subsequent ACL checks. A
thread-local is the lowest-common-denominator: every Odoo worker handles
one request per thread, so per-thread storage gives us a stable channel
for the role id regardless of which auth path was taken.
"""

import logging
import threading

import psycopg2
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

# Postgres raises one of these when two requests touch the same row
# concurrently. Expected under load on a shared API key, not a fault.
# Mirrors odoo.service.model.PG_CONCURRENCY_EXCEPTIONS_TO_RETRY, spelled
# out here rather than imported so a model doesn't reach into a service.
CONCURRENT_UPDATE_ERRORS = (
    psycopg2.errors.SerializationFailure,
    psycopg2.errors.DeadlockDetected,
    psycopg2.errors.LockNotAvailable,
)

# Per-thread storage for the API-key role attribution. Cleared at the
# start of every _check_credentials call so a stale value from a prior
# request on the same worker thread can't leak. Read by res.users
# ._get_api_key_role().
_mcp_thread_local = threading.local()


def get_thread_api_key_role_id():
    return getattr(_mcp_thread_local, "api_key_role_id", None)


def set_thread_api_key_role_id(role_id):
    _mcp_thread_local.api_key_role_id = role_id


def clear_thread_api_key_role_id():
    if hasattr(_mcp_thread_local, "api_key_role_id"):
        del _mcp_thread_local.api_key_role_id


class ResUsersApikeys(models.Model):
    _inherit = "res.users.apikeys"

    def init(self):
        super().init()
        # The parent has _auto = False and manages its own schema. Add our
        # columns explicitly so they exist before any migration runs.
        #
        # `auth_totp.device` inherits this model by prototype (`_inherit`
        # with a distinct `_name`, also `_auto = False`), so Odoo copies our
        # x_* fields onto its own `auth_totp_device` table too. That model
        # defines no init() of its own, so THIS override runs for it as well.
        # Key every statement on `self._table` so the columns land on
        # whichever table is being initialised (res_users_apikeys OR
        # auth_totp_device). Hard-coding "res_users_apikeys" left
        # auth_totp_device without the columns, which crashed the user form
        # with `UndefinedColumn: auth_totp_device.x_role_id` as soon as it
        # snapshotted the user's trusted TOTP devices.
        table = SQL.identifier(self._table)
        self.env.cr.execute(
            SQL(
                """
            ALTER TABLE %s
            ADD COLUMN IF NOT EXISTS x_role_id integer,
            ADD COLUMN IF NOT EXISTS x_state varchar DEFAULT 'active',
            ADD COLUMN IF NOT EXISTS x_last_used timestamp without time zone,
            ADD COLUMN IF NOT EXISTS x_use_count integer DEFAULT 0
            """,
                table,
            )
        )
        self.env.cr.execute(
            SQL(
                "CREATE INDEX IF NOT EXISTS %s ON %s (x_role_id)",
                SQL.identifier(f"{self._table}_x_role_id_idx"),
                table,
            )
        )
        self.env.cr.execute(
            SQL(
                "CREATE INDEX IF NOT EXISTS %s ON %s (x_state)",
                SQL.identifier(f"{self._table}_x_state_idx"),
                table,
            )
        )

    x_role_id = fields.Many2one(
        comodel_name="res.users.role",
        string="Role",
        ondelete="restrict",
        index=True,
        help="The role this key represents. The key's effective permissions "
        "during any request are exactly this role's groups — never broader "
        "than the owning user, and never broader than this role.",
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
    def _check_role_subset_of_user(self):
        """A key cannot grant more permissions than its owning user has.

        This is the real security invariant. We deliberately do NOT require
        the role to be assigned to the user via OCA role_line_ids — that
        would trigger OCA's enforcement and strip the user of unrelated
        UI groups (Audit Log menu, Settings access, etc.). See ADR-014.
        """
        for rec in self:
            if not rec.x_role_id:
                continue
            excess = rec.x_role_id._mcp_excess_group_ids(rec.user_id)
            if excess:
                missing = self.env["res.groups"].browse(list(excess)).mapped("display_name")
                raise ValidationError(
                    _(
                        "Role '%(role)s' includes groups that user '%(user)s' "
                        "does not have: %(missing)s. A key cannot grant more "
                        "than its owner.",
                        role=rec.x_role_id.display_name,
                        user=rec.user_id.login,
                        missing=", ".join(missing),
                    )
                )

    def _check_credentials(self, *, scope, key):
        """Override: stash matched key id + role id for the duration of
        this request, both on the request session (modern path) and on
        a thread-local (covers the legacy /jsonrpc path where the
        request is popped from the stack during dispatch_rpc).

        Fails closed: if the key is suspended/revoked, deny.
        """
        # Reset any leftover thread-local from a previous request on this
        # worker thread. Belt-and-braces: also reset the session.
        clear_thread_api_key_role_id()

        user_id = super()._check_credentials(scope=scope, key=key)
        if not (user_id and key):
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
                "MCP Pro Governance: failed to resolve API key id; denying request to fail closed."
            )
            return None  # fail closed

        if len(rows) != 1:
            _logger.warning(
                "MCP Pro Governance: expected 1 matching key for "
                "user_id=%s index=%s, found %d. Denying request.",
                user_id,
                index,
                len(rows),
            )
            return None  # fail closed

        api_key_id, role_id, state = rows[0]

        if state != "active":
            _logger.warning(
                "MCP Pro Governance: API key id=%s is %s; denying request.",
                api_key_id,
                state,
            )
            return None  # fail closed

        # Modern path: write to session if a request is on the stack.
        if request:
            request.session["x_mcp_api_key_id"] = api_key_id
            if role_id:
                request.session["x_mcp_api_key_role_id"] = role_id
        # Always: thread-local. Survives borrow_request() in /jsonrpc.
        if role_id:
            set_thread_api_key_role_id(role_id)
        # Audit-log snapshot: stash the resolved key id so the legacy
        # /jsonrpc and /xmlrpc paths (where request is popped) still
        # record `x_api_key_id` on the auditlog.http.request row.
        from .ir_http import set_audit_api_key_id

        set_audit_api_key_id(api_key_id)

        # Lightweight usage counter; one UPDATE per call. Promote to a
        # deferred / batched update if it becomes a hot path.
        #
        # Best-effort by design: it runs on the auth path, so it must never
        # deny a valid key. Concurrent calls on one key update this row at
        # once and the loser gets a SerializationFailure, which retrying()
        # would retry but never sees — _authenticate_explicit() wraps auth in
        # `except Exception: raise AccessDenied()`, making it a 403 first. The
        # savepoint stops that from poisoning the request transaction. A lost
        # increment costs nothing: both columns are readonly display fields.
        try:
            with self.env.cr.savepoint(flush=False):
                self.env.cr.execute(
                    "UPDATE res_users_apikeys "
                    "SET x_last_used = now() at time zone 'utc', "
                    "    x_use_count = x_use_count + 1 "
                    "WHERE id = %s",
                    (api_key_id,),
                )
        except CONCURRENT_UPDATE_ERRORS:
            _logger.debug(
                "MCP Pro Governance: usage counter for API key id=%s skipped, "
                "concurrent update on the same key. Authentication unaffected.",
                api_key_id,
            )
        except psycopg2.Error:
            _logger.warning(
                "MCP Pro Governance: usage counter for API key id=%s failed. "
                "Authentication unaffected.",
                api_key_id,
                exc_info=True,
            )
        return user_id
