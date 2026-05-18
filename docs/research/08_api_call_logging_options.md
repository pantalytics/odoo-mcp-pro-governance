# 08 — API call logging: implementation options

**Status:** decision pending (2026-05-12)
**Driver:** after a real user installed the addon and made an MCP call, no row appeared in the API Call Log. Root cause: the v0.1 module ships log models but no writer. This memo captures what's available and which path closes the gap.

## Problem

`mcp.governance.api.call.log` and `mcp.governance.audit.log` are defined but never written to. The MCP server lives outside Odoo and authenticates as a regular user via JSON-RPC/XML-RPC — Odoo has no built-in mechanism to persist one row per inbound RPC call and surface it in the UI.

Confirmed by grep: `mcp.governance.api.call.log` is referenced only by its own model, views, and tests. No controller, dispatch hook, `base_automation` rule, or external push exists.

## What Odoo and OCA already provide

### Odoo standard

- `ir.logging` — persists Python `logging` records when `--log-db` is set. Not request-aware (no method/model/payload). Wrong tool.
- `res.users.log` — one row per *session start*, not per call. Wrong granularity.
- `--log-handler=odoo.http.rpc.request:DEBUG` — emits per-call lines to stdout/log file, unstructured, not queryable from the UI.

No first-class "log inbound RPC call to a DB table" facility in Odoo core.

### OCA `auditlog` (server-tools, 19.0)

Verified live on `OCA/server-tools` branch `19.0`: module `auditlog`, manifest version `19.0.1.0.1`, license **AGPL-3**.

Models shipped:

| Model | Purpose |
|---|---|
| `auditlog.rule` | Per-model opt-in: choose which models to track and which ops (create/read/write/unlink + custom methods). |
| `auditlog.log` | One row per ORM action that matches a rule. FK to `auditlog.http.request`. |
| `auditlog.log.line` | Per-field old/new values for the action above. |
| `auditlog.http.request` | One row per HTTP request: path, root URL, user, context. Lazily created on first matching ORM action. |
| `auditlog.http.session` | Groups HTTP requests into sessions. |

The HTTP request log + correlation FK is exactly the pattern this addon's `x_request_id` was hand-rolling. The rule mechanism naturally bounds DB growth: only modeled actions trigger rows.

This corrects an earlier research note that claimed no 19.0 port existed — it does, see [OCA shop page](https://apps.odoo-community.org/shop/audit-log-533) (version dropdown lists 19.0) and the [19.0 branch on GitHub](https://github.com/OCA/server-tools/tree/19.0/auditlog).

### Other OCA modules surveyed

| Module | Repo | Verdict |
|---|---|---|
| `tracking_manager` | server-tools | Per-field change tracking; no HTTP envelope. Latest 18.0. Not a fit. |
| `rest_log` | rest-framework | Logs requests only for OCA `base_rest`-routed endpoints; ignores JSON-RPC/XML-RPC. No 19.0. Not a fit. |
| `session_db` | server-tools | Moves sessions to DB. Orthogonal. |
| `sentry` | server-tools | Forwards errors to Sentry. External, not in-UI. |

## Three implementation paths

### A. Depend on OCA `auditlog`

`__manifest__.py` gains `"depends": ["base", "auditlog"]`. Our addon becomes a thin configurator + UI skin:

- Seed default `auditlog.rule` records on install for common models (`sale.order`, `res.partner`, `account.move`, …) filtered by user (only the technical MCP-bot user matters).
- "MCP Pro → API Call Log" menu becomes an `ir.actions.act_window` on `auditlog.http.request` with a domain filtering to users marked `x_log_api_calls`.
- "MCP Pro → About" menu with positioning copy + link to the SaaS.
- Drop our `mcp.governance.audit.log` and `mcp.governance.api.call.log` entirely.

Estimated module size: **~50 LOC** (data XML for rules + menu + view actions).

**License consequence:** AGPL-3 is viral on linked code. Our module must re-license from LGPL-3 to AGPL-3. Acceptable for a €0 App Store companion with no proprietary IP to protect, but a one-way decision.

### B. Roll our own

Override `Model._call_kw` (or `http.Controller._dispatch`) to write one row per JSON-RPC/XML-RPC call: user, path, ORM method, model, status, duration, request id, IP.

- Per-user `x_log_api_calls` boolean on `res.users`, default off. Operator flags the MCP-bot user. Hook checks the flag → bounded DB growth.
- Keep `mcp.governance.api.call.log` (drop `x_agent_identity_id`, drop the audit-log correlation field; the audit-log model goes away).
- Drop `mcp.governance.agent.identity` and `mcp.governance.audit.log`.

Estimated module size: **~150 LOC**.

**License consequence:** LGPL-3 stays. No external dependency. We own and maintain the dispatch hook across Odoo versions.

### C. Fork OCA `auditlog`

Copy `auditlog` into this repo, strip rule/CRUD parts we don't want, rebrand.

**Why not:** Inherits every downside of A (still AGPL-3 — fork is a derivative) *and* every downside of B (we maintain the copy across Odoo versions). Attribution requirements (ABF OSIELL 2015, OCA) remain in every file. App Store reviewers and the OCA community treat thin reskins of OCA modules as a red flag. No upside specific to forking that depending doesn't deliver.

## Recommendation

**Path A.** OCA already solved the hard parts (HTTP request envelope, session grouping, cleanup cron, model-rule scoping). Our differentiated value-add is the AI-agent framing — sane defaults for which models to log, a dedicated MCP-bot user, onboarding that explains the picture — not re-implementing what `auditlog` ships. Module shrinks to ~50 LOC, AGPL-3 acceptable for a €0 companion.

If the license switch becomes a blocker downstream (unlikely for a free addon, possible if future commercial features merge in), Path B is the fallback.

## Open decisions (carried to next session)

1. Confirm Path A (depend on `auditlog`) vs. B (roll our own) — current preference: A.
2. License switch LGPL-3 → AGPL-3 in `__manifest__.py`, `LICENSE`, `README.md` — required for A.
3. Module version bump: `19.0.0.2.0` (drops `agent_identity` + `audit_log` tables).
4. Migration script in `migrations/19.0.0.2.0/` to drop the two now-unused tables on upgrade.
5. Naming: keep `mcp.governance.*` (technical only, not user-visible) or rename now while the table is small.

## Sources

- [OCA/server-tools `auditlog` on 19.0](https://github.com/OCA/server-tools/tree/19.0/auditlog) — manifest `19.0.1.0.1`, license AGPL-3
- [OCA shop — Audit Log (533)](https://apps.odoo-community.org/shop/audit-log-533) — 19.0 listed in version dropdown
- [OCA/rest-framework `rest_log`](https://github.com/OCA/rest-framework) — scope limited to `base_rest`
- [Odoo forum: how to see RPC calls](https://www.odoo.com/forum/help-1/how-can-i-see-which-api-calls-are-made-to-learn-what-odoo-is-doing-at-specific-times-183911)
