# Architecture Decision Records — `pan_mcp_pro_governance`

Decisions that shape this addon. Each record states the **context**, the **decision**, and the **consequences** (good and bad). Newer ADRs may supersede older ones — older entries stay in place as history.

Format follows [Michael Nygard's ADR template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions). Research that informed these decisions lives in [../research/](../research/); the ADRs are the *commitments* derived from that research.

## Status legend

- **Accepted** — the decision is in force.
- **Proposed** — written down, not yet committed; waiting on alignment.
- **Superseded** — replaced by a later ADR (link forward).
- **Deprecated** — no longer applies; reasons in the record.

## Index

| # | Title | Status |
|---|---|---|
| [001](001-license-agpl-3.md) | License switch LGPL-3 → AGPL-3 in v0.2.0 | Accepted |
| [002](002-depend-on-oca-auditlog.md) | Depend on OCA `auditlog` for HTTP + ORM audit | Accepted |
| [003](003-drop-v01-log-models.md) | Drop v0.1 `audit_log` and `api_call_log` models | Accepted |
| [004](004-keep-agent-identity-as-spine.md) | Keep `mcp.governance.agent.identity` as governance spine | Accepted |
| [005](005-odoo-per-user-billing-constraint.md) | Constraint: Odoo per-user billing as architectural input | Accepted |
| [006](006-per-api-key-attribution.md) | v0.3 strategy: per-API-key attribution via patched auth flow | Proposed |
| [007](007-base-user-role-optional-dep.md) | Optional integration with OCA `base_user_role` for RBAC | Superseded by 010 |
| [008](008-context-tagging-fallback.md) | Context-tagging as no-patch fallback to per-API-key attribution | Proposed |
| [009](009-scoped-api-keys.md) | Scoped API keys (Airtable-PAT-inspired): parallel scope system on `res.users.apikeys` | Superseded by 010 |
| [010](010-api-key-bound-to-role.md) | API key bound to a single OCA `base_user_role` — narrow effective groups per request | Proposed |

## How to add a new ADR

1. Copy the most recent ADR file, increment the number, update title and status.
2. Add a row to the index above.
3. Keep it short — one screen if possible. ADRs document a *decision*, not a tutorial.
