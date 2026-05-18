# ADR-007: Integrate optionally with OCA `base_user_role` for RBAC

**Status:** Superseded by [ADR-010](010-api-key-bound-to-role.md) — `base_user_role` is promoted from optional to required dependency (2026-05-18)

> **Superseded note**: ADR-010 makes `base_user_role` a **hard** dependency because the per-API-key role-binding design centrally relies on it. The optional-integration framing in this ADR no longer applies. Kept as history for the reasoning about composition vs. replacement.

## Context

Once [ADR-006](006-per-api-key-attribution.md) gives us "**who** called Odoo" at API-key resolution, the natural next question is "**what is this agent allowed to do**." Odoo's native answer is `res.groups` + `ir.model.access` + `ir.rule`. Stacking groups by hand on a shared bot user works but doesn't scale to multiple agents with different scopes.

OCA `base_user_role` (19.0.1.0.2, AGPL-3, in [OCA/server-backend](https://github.com/OCA/server-backend/tree/19.0)) introduces a `res.users.role` model — a named bundle of `res.groups` with optional company-binding and date-binding. Users get one or more roles, roles expand to underlying groups. It is purely a composition layer; it does not change Odoo's billing or auth flow.

## Decision (proposed)

Make OCA `base_user_role` an **optional** dependency, not a hard one. When present, our addon:

- Adds `x_role_id = fields.Many2one("res.users.role")` to `mcp.governance.agent.identity` (visible only when `base_user_role` is installed — guarded by a feature-check).
- Documents the recommended pattern: define roles like `ai-sales-reader`, `ai-cron-full`, `ai-claude-readonly`; assign roles to the shared bot user; bind each `agent_identity` to one role for documentation.
- Surfaces the role's effective `res.groups` on the agent form so operators can audit "what can this agent actually do" without clicking through Odoo's group editor.

When `base_user_role` is not installed, the addon works unchanged but the role field is hidden and the documentation falls back to "edit groups directly on the bot user."

## Consequences

**Positive**
- Customers who already use OCA RBAC get a seamless extension into AI agent governance.
- The "role" abstraction lines up with how compliance frameworks (ISO 42001, NIST AI RMF) think about agent roles — easier to map to controls.
- Optional dependency means we don't push extra installs on customers who don't need RBAC granularity.

**Negative**
- Optional dependencies in Odoo are fiddly: feature detection via `env['ir.module.module'].search(...)`, runtime guards on view rendering, and separate XML files conditionally loaded. Maintenance overhead.
- The user-side question ("can my agent do X") becomes a two-step lookup (`agent_identity.x_role_id.implied_ids` → `ir.model.access` resolution) that's not trivial to visualize.
- `base_user_role` operates on `res.users`, not on API keys. So in our N-keys-on-one-user model, all agents on the same user share the same role set. To get per-agent ACL differentiation we would need to wire ACLs through API-key-id, which OCA does not (and Odoo does not natively) do. That's a v0.4+ research question.

## Alternatives considered

- **Hard dependency on `base_user_role`** — rejected because it forces an install on customers whose use case is purely audit (one agent, simple permissions). Cleanest is opt-in.
- **Replicate role logic in our addon** — rejected, NIH. OCA's implementation is mature.
- **Skip RBAC entirely for now** — rejected because role-thinking is a near-term governance need, especially for EU AI Act Art. 13 transparency obligations ("what is this AI authorized to do").

## Open questions

1. Is OCA `base_user_role` 19.0 stable enough to recommend in our App Store description? Last commit cadence and open-issue count to check before promoting Proposed → Accepted.
2. Does pinning to a specific `base_user_role` version create upgrade friction for customers who run Odoo.sh and lag OCA releases? May need a wide compatibility range.
