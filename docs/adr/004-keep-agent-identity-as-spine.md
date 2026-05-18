# ADR-004: Keep `mcp.governance.agent.identity` as the governance spine

**Status:** Accepted (2026-05-18)

## Context

When narrowing v0.2 scope to "just close the logging gap" ([ADR-002](002-depend-on-oca-auditlog.md), [ADR-003](003-drop-v01-log-models.md)) the question came up: do we drop `mcp.governance.agent.identity` too? It's currently used only as a label and the OCA `auditlog` records already capture `user_id` directly.

Counter-pressure: the long-term direction is **broader AI governance** (policies, quotas, risk tiers, approval workflows for high-impact actions, EU AI Act Art. 12/13 mappings, cost attribution per agent). Every one of those features needs *something* to attach to.

## Decision

Keep `mcp.governance.agent.identity` in v0.2.0 as the **central spine future governance features attach to**. Strip it to the minimum useful set:

- `name`, `state` (draft/active/suspended/revoked), `x_provider`, `x_user_id` (Many2one → `res.users`), `x_owner_id`, `x_description`.
- Smart-button `action_view_api_calls` → filtered `auditlog.http.request` for this agent's user (in v0.3 this filter shifts to API key — see [ADR-006](006-per-api-key-attribution.md)).
- Lifecycle actions (`action_activate`, `action_suspend`, `action_revoke`).

Do NOT add policies, quotas, or risk tiers in v0.2. Those land in later releases on top of this spine.

## Consequences

**Positive**
- Future features (per-agent quotas, risk classification, approval flows) attach to a stable model without schema rework.
- `agent_identity` is what makes our addon different from "just install OCA auditlog and configure rules" — it's the AI-agent-framed UI that turns generic audit into governance.
- Operators get a single page "who is this agent, who owns it, what state is it in, what has it done" — the EU AI Act Art. 26 deployer obligation is easier to demonstrate.

**Negative**
- One more model the customer has to populate. Friction in onboarding.
- The `x_user_id` binding is currently 1:1 with `res.users` — meaning N agents on one shared user (the realistic deployment, see [ADR-005](005-odoo-per-user-billing-constraint.md)) require a different attribution primitive ([ADR-006](006-per-api-key-attribution.md)).
- We carry the maintenance cost of a model whose value is mostly in features that don't exist yet.
