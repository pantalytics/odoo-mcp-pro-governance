# ADR-002: Depend on OCA `auditlog` for HTTP and ORM audit trail

**Status:** Accepted (2026-05-18)

## Context

v0.1 shipped two append-only models — `mcp.governance.audit.log` (per-record ORM trail) and `mcp.governance.api.call.log` (per-HTTP-request log). Neither was populated by any code path; both tables stayed empty after install. The MCP server lives outside Odoo and writes nothing back to these tables, and we never wrote the inbound side either.

We evaluated three paths to close this gap (see [research/08](../research/08_api_call_logging_options.md)):

- **A.** Depend on OCA `auditlog` (HTTP request + session + per-record CRUD already implemented, 19.0 port exists).
- **B.** Roll our own dispatch hook on `Model._call_kw` or `Controller._dispatch` (~150 LOC).
- **C.** Fork OCA `auditlog` (inherits AGPL-3, adds maintenance burden, no upside over A).

End-to-end validation against pantalytics.odoo.com (2026-05-18) confirmed OCA `auditlog` captures the modern Odoo JSON-RPC routes (`/json/2/<model>/<method>`) that MCP servers use, including the HTTP-request → ORM-action correlation we hand-built in v0.1.

## Decision

Depend on **OCA `auditlog`** (`19.0.1.0.1`, AGPL-3). Our addon becomes a thin configuration layer + AI-agent UI skin over their data model.

Concretely:
- `__manifest__.py` adds `"auditlog"` to `depends`.
- `pan_mcp_pro_governance` ships seed `auditlog.rule` records for AI-relevant target models via a `post_init_hook` (conditional: only for models whose owning module is installed).
- Our "API Call Log" menu becomes an `ir.actions.act_window` over `auditlog.http.request`.
- Our user/manager groups imply `auditlog.group_auditlog_user` / `auditlog.group_auditlog_manager`.

## Consequences

**Positive**
- ~50 LOC of configuration vs ~150 LOC of dispatch hook. Less to maintain.
- Battle-tested HTTP request + session + cleanup cron come for free.
- Rule-based scoping bounds DB growth (only the models the operator opts in to).
- Customers get OCA's tooling (e.g. existing auditlog filters, autovacuum cron) "for free."

**Negative**
- AGPL-3 viral license requirement (handled in [ADR-001](001-license-agpl-3.md)).
- Customer must install both modules. OCA `auditlog` not on Odoo's official App Store, so on Odoo.sh / on-prem they need the OCA submodule too.
- Default rule states are `draft` until operator subscribes — there's an onboarding step we have to teach.
- We inherit OCA's design constraints (e.g. `auditlog.http.request.user_context` is plain Char, not JSON; query patterns must accommodate).
