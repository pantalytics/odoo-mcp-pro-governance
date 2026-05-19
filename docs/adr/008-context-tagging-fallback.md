# ADR-008: Context-tagging as no-patch fallback to per-API-key attribution

**Status:** Superseded by [ADR-010](010-api-key-bound-to-role.md) (2026-05-19)
**Relates to:** [ADR-006](006-per-api-key-attribution.md)

> **Superseded note (2026-05-19):** Never built. ADR-010 made the
> stronger "API key bound to a role" mechanism the primary attribution
> path. Context-tagging was attractive as a no-patch escape hatch but
> the patch in ADR-010 turned out to be small and worth shipping
> upfront. Kept here as history — if the patch becomes unmaintainable
> against future Odoo versions, this is the documented fallback.

## Context

[ADR-006](006-per-api-key-attribution.md) proposes patching Odoo's `_check_credentials` to thread API key identity through to the audit log. That patch is small but invasive — it overrides a low-level auth method on `res.users.apikeys`. Customers running a hardened Odoo (e.g. via `manifest_check`, custom security audit) may refuse to install modules that override core auth. We also want a path that works *before* v0.3 ships.

OCA `auditlog.http.request` already has a field `user_context = fields.Char` that captures `request.env.context` on every audited HTTP call. If the calling integration injects a recognizable tag into context, that tag survives unchanged into the audit log without any patch on our side.

## Decision (proposed)

Ship a **fallback attribution path** based on integrations self-tagging their context, in addition to (not instead of) [ADR-006](006-per-api-key-attribution.md).

Concretely:

1. Document an integration-side contract: every MCP call passes `context={'mcp_agent_key': '<unique-key>', 'mcp_agent_name': '<friendly>'}`.
2. `mcp.governance.agent.identity` gets a `x_context_key` field (unique per agent) that operators copy into their integration's config.
3. Our smart-button / compute queries `auditlog.http.request.user_context ilike '%mcp_agent_key%<key>%'`.
4. v0.3 ships [ADR-006](006-per-api-key-attribution.md) as the primary, **stronger** mechanism. Context-tagging stays available as a fallback for the cases below.

## When to use which

| Scenario | Primary mechanism |
|---|---|
| Integration uses Odoo API key, runs in supported Odoo 19 release line | [ADR-006](006-per-api-key-attribution.md) (server-verified, strongest) |
| Customer refuses core-auth patches; or OCA `auditlog` not installed | This ADR (self-attested, sufficient for non-adversarial environments) |
| Integration runs via session-cookie auth, not API key | This ADR (no key id to capture) |
| Hostile or buggy integration that might mis-tag itself | [ADR-006](006-per-api-key-attribution.md) — context tagging cannot be trusted there |

## Consequences

**Positive**
- Zero patch to Odoo core. Works on any Odoo 19 install that has OCA `auditlog`.
- Ship-able in v0.2.x without waiting for [ADR-006](006-per-api-key-attribution.md) implementation.
- Customers can adopt the agent identity model immediately, then upgrade to key-based attribution when v0.3 lands.

**Negative**
- **Self-attestation, not cryptographic.** A misbehaving or hostile integration can tag itself as another agent. Acceptable for governance within one organization where all integrations are trusted; not acceptable for cross-trust-boundary scenarios (e.g. SaaS multi-tenant MCP server attributing to per-tenant identity).
- Requires the integration to be modified to inject the tag. For our own MCP Pro server we control this; for third-party MCP clients we must document and persuade.
- `user_context` is plain Char. Querying with `ilike` works at small scale but becomes a hot path at high volume. A computed indexed field on the agent identity side mitigates this for the smart-button use case.
- Coexistence with [ADR-006](006-per-api-key-attribution.md) creates two columns to look at (`x_api_key_id` and parsed `user_context`); operator UI needs to clearly show which signal was used to attribute a given call.

## Open questions

1. Should the context key be the same value as the API key id, the api key name, or a separate `agent_identity.x_context_key`? Probably the latter — decouples the wire-level tag from any specific auth mechanism, so the tag survives if a customer rotates API keys.
2. Do we need a write-time validation that rejects integrations using context tags that don't match any registered `agent_identity`? Could surface misconfiguration faster but might break legitimate one-off scripts.
