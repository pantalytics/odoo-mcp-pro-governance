# ADR-009: Scoped API keys (Airtable-PAT-inspired) — design proposal

**Status:** Superseded by [ADR-010](010-api-key-bound-to-role.md) (2026-05-18 — same day)
**Depends on:** [ADR-005](005-odoo-per-user-billing-constraint.md), [ADR-006](006-per-api-key-attribution.md)
**Related research:** [research/08](../research/08_api_call_logging_options.md)

> **Superseded note (2026-05-18):** This ADR proposed a custom parallel scope system on `res.users.apikeys` (`x_scope_model_ids`, `x_scope_methods`, etc.) enforced via `Model._call_kw` overrides. A cleaner alternative — binding each API key to a single OCA `base_user_role` role and reusing Odoo's native group / ACL / record-rule machinery — was identified the same day during a design conversation. See [ADR-010](010-api-key-bound-to-role.md) for the chosen design. This ADR is kept as history because (1) it documents the path not taken and the reasoning, and (2) if `base_user_role` ever becomes unviable, the parallel-system approach is the fallback.

## Context

[ADR-006](006-per-api-key-attribution.md) tells us **who** called Odoo (which API key). [ADR-007](007-base-user-role-optional-dep.md) tells us **what an agent is allowed to do** at the user level via OCA `base_user_role`. Both still leave a gap: every API key inherits the **full** access of its owning user. If five integrations share one Internal User (per [ADR-005](005-odoo-per-user-billing-constraint.md)), they each have admin-level reach if the owning user does — even though most of them only need to read `res.partner` or write `crm.lead`.

Odoo Support confirmed in writing (2026-05-18):

> "API keys are always tied to a user, so they inherit that user's access rights. There is currently no built-in way to create scoped API tokens with limited permissions independent of a user."
> — Heather, Odoo Live Chat

The well-established design pattern that addresses this is the **personal access token (PAT) with per-token scopes**, popularised by GitHub, Slack, and most directly Airtable.

### Reference model: Airtable PATs

Airtable separates two axes per token:

| Axis | Meaning | Example |
|---|---|---|
| **Scopes** | What kinds of actions the token can perform | `data.records:read`, `data.records:write`, `schema.bases:write` |
| **Resources** | Where those actions can be performed | A single base, multiple bases, "all current and future bases in owned workspaces" |

Net effect: a token can read records in Base A only, while the owning user retains full admin rights everywhere. The token itself is still tied to a human user (that's the legal/billing identity), but the *capability surface* is per-token. Revocation is per-token. ([Airtable PAT docs](https://airtable.com/developers/web/guides/personal-access-tokens), [Scopes reference](https://airtable.com/developers/web/api/scopes))

Things Airtable does well that we can copy:
- Composable: scope × resource = grant; both required.
- Named scopes with `:read` / `:write` / `:manage` suffix grammar — readable in UI.
- Resource picker with three granularities (single / multi / all-owned).
- Per-token revocation independent of the user.

Things Airtable doesn't do that we could improve:
- No usage analytics / last-used display per token.
- No mandatory expiration.
- No IP allowlist.
- No rate limit per token.

## Decision (proposed)

Add **scoped API keys** to this addon as an `_inherit` on `res.users.apikeys`. The key still belongs to one user (Odoo constraint, [ADR-005](005-odoo-per-user-billing-constraint.md)) — but our addon enforces a *narrower* capability surface than that user has, when a request authenticates with the key.

### Data model

Extend `res.users.apikeys`:

```python
class ResUsersApikeys(models.Model):
    _inherit = "res.users.apikeys"

    # === Scope (the "what") ===
    x_scoped = fields.Boolean(
        string="Apply scope restrictions",
        default=False,
        help="If unchecked, the key inherits the full access of its user (default Odoo behaviour).",
    )
    x_scope_model_ids = fields.Many2many(
        comodel_name="ir.model",
        string="Allowed Models",
        help="Empty = same as user; populated = key may only operate on these models.",
    )
    x_scope_methods = fields.Selection(
        selection=[
            ("read", "Read only"),
            ("write", "Read + Write"),
            ("create", "Read + Write + Create"),
            ("full", "Full (incl. Unlink)"),
        ],
        default="read",
        help="Maximum operation level. Cannot exceed the user's own access.",
    )

    # === Resource (the "where") ===
    x_scope_company_ids = fields.Many2many(
        comodel_name="res.company",
        string="Allowed Companies",
        help="Empty = all of user's companies; populated = key restricted to these.",
    )
    x_scope_domain = fields.Char(
        string="Extra Record Filter",
        help="Optional Odoo domain (e.g. [('state', '=', 'draft')]) applied on top of "
             "the user's own record rules. Advanced; leave empty in normal cases.",
    )

    # === Lifecycle + observability ===
    x_state = fields.Selection(
        selection=[("active", "Active"), ("suspended", "Suspended"), ("revoked", "Revoked")],
        default="active",
    )
    x_last_used = fields.Datetime(readonly=True)
    x_use_count = fields.Integer(readonly=True, default=0)
    x_ip_allowlist = fields.Char(
        help="Comma-separated list of CIDRs. Empty = no IP restriction.",
    )

    # === Governance link ===
    x_agent_identity_id = fields.Many2one(
        "mcp.governance.agent.identity",
        string="Agent Identity",
        help="Which named AI agent this key represents.",
    )
```

### Enforcement layer

Three small hooks:

1. **`_check_credentials` override** (already in [ADR-006](006-per-api-key-attribution.md)). Additional logic: if the matched key has `x_state != 'active'`, deny. If `x_ip_allowlist` is set and remote IP doesn't match, deny. Update `x_last_used` and `x_use_count`. Stash the key id on `request.session.x_mcp_api_key_id`.

2. **`Model._call_kw` override** on `base`. When `request.session.x_mcp_api_key_id` is present:
   - Resolve the key (cached, one query per request).
   - If `x_scoped == True`, check `self._name in key.x_scope_model_ids.mapped('model')` — else raise `AccessError`.
   - Check requested method against `x_scope_methods` — `read` only allows read; `write` allows read+write; etc.
   - If `x_scope_company_ids` set and current company not in list, raise `AccessError`.
   - If `x_scope_domain` set, append it to `Model._where_calc` (or use a lightweight `ir.rule` injection).

3. **`auditlog.http.request` inherit** (already in [ADR-006](006-per-api-key-attribution.md)) carries `x_api_key_id`. When a call is *denied* by scope, write a deny-record with reason — so operators can see "this key tried `unlink` on `account.move` and was blocked at 14:23."

### UI

Add a tab "Scope" to the existing API Key form, mirroring Airtable's two-section layout:

```
┌─ API Key: cron-sync-2026 ───────────────────────────────────┐
│ User: pantalytics-bots@…                Status: ● Active    │
│ Created: 2026-01-15        Last used: 2026-05-18 14:21      │
│ Use count: 4,328           Expires: never (recommend 1y)    │
│                                                              │
│ ┌─ Scope ──────────────────────────────────────────────────┐│
│ │ [✓] Apply scope restrictions                             ││
│ │                                                           ││
│ │ Allowed Models     [+] res.partner   [+] crm.lead        ││
│ │                    [+] sale.order                         ││
│ │ Operations         ( ) Read only                          ││
│ │                    (●) Read + Write                       ││
│ │                    ( ) Read + Write + Create              ││
│ │                    ( ) Full (incl. Unlink)               ││
│ │ Companies          [All user's companies]                 ││
│ │ Extra Filter       (empty)                                ││
│ │ IP Allowlist       (empty)                                ││
│ │                                                           ││
│ │ Agent Identity     [→ MCP Cron Sync Bot]                 ││
│ └───────────────────────────────────────────────────────────┘│
│                                                              │
│ [Suspend]  [Revoke]  [Rotate key]                            │
└──────────────────────────────────────────────────────────────┘
```

Smart-button on `mcp.governance.agent.identity` → "API Keys" filtered on `x_agent_identity_id`.

## Consequences

**Positive**
- **Principle of least privilege** becomes operational for AI integrations on a single billable user. The cron sync gets a write-only-on-crm.lead key; Claude gets a read-on-everything-plus-write-on-sale.order key; n8n gets a comment-only key. Each can be revoked independently.
- **Defence in depth**: even if an attacker steals one key, blast radius is bounded to that key's scope, not the whole user's access.
- **Audit-grade**: deny-events are logged. Operators see "this AI agent tried something it shouldn't" as first-class signals, not just successful calls.
- **Aligned with [ADR-005](005-odoo-per-user-billing-constraint.md)**: no extra Internal Users. The economic story holds — "per-agent governance on a shared user."
- **Differentiator**: this is the feature that turns the addon from "configurator over OCA auditlog" into a real governance product. Odoo doesn't have it, OCA doesn't have it, no other Odoo MCP project has it.

**Negative**
- **Adds enforcement to a hot path** (`_call_kw` runs on every ORM call). The per-request key lookup must be cached aggressively — one DB hit per request, not per call. We need a registry-level cache or `request`-level memo.
- **Edge cases**: computed fields, related fields, on-change methods, server actions — all may trigger ORM calls on models *not* in the key's scope as a side-effect of a "legitimate" call. We need to think hard about whether scope enforcement applies to direct calls only, or also to ORM internals triggered by them. Probably: only direct, with a documented escape hatch (`with_context(bypass_api_key_scope=True)` for internal recursion).
- **Two parallel permission systems** (Odoo's groups/ACLs/rules AND our key scope) — operators must understand the AND-composition. We document this prominently.
- **Migration of existing keys**: existing `res.users.apikeys` rows default to `x_scoped = False`, behaving exactly as today. Customers opt in per key. No forced upgrade.
- **Self-attestation gap closed for malicious clients**: this addresses what [ADR-008](008-context-tagging-fallback.md) couldn't. But it doesn't help if the *user* is malicious — if Rutger is compromised, his keys are too. Standard Odoo problem; out of scope here.

## How this composes with prior ADRs

```
ADR-005 ────────────────────────────────────────────────┐
(Odoo bills per user — keep ONE shared user)            │
                                                         │
ADR-006 ── ADR-009 ──────────────────────────────────── │
(carry key id forward) (per-key scope on that id)       ▼
                                                  one paid user
ADR-007 (optional) ─── (RBAC at user-role level)  ↕ no extra cost
                                                  N independently-
ADR-008 (fallback) ─── (context tag when key      scoped agents
                       attribution not feasible)
                                                  with cryptographic
                                                  identity + scope
                                                  guarantees
```

## Open questions

1. **Single `x_scope_methods` selection vs. multiple booleans** (Airtable's `:read`/`:write` separate scope strings). The selection is simpler but less composable — what if someone wants "create + unlink but not write"? Probably never in practice. Start with selection; promote to M2M if needed.
2. **Should we mirror Airtable's `schema.*:write` for "can alter models/fields"?** This maps to model creation, field definition via UI — typically only sysadmin uses this. Could be a separate `x_scope_schema_write` boolean, default False.
3. **Method-level (not model-level) scoping** — e.g. allow `read` and `create` on `crm.lead` but not custom methods like `action_set_won`. Airtable doesn't go this deep. We could add `x_scope_method_blocklist` for the paranoid 5%, default empty.
4. **Rate limits per key**. Airtable doesn't expose this. Operationally valuable for AI integrations that can fire 5,000 calls/hour. Defer to v0.4+.
5. **Should we contribute the enforcement layer to OCA?** Upstream-first benefits everyone but slows our shipping cadence. Likely path: ship in our addon first, propose as `auth_apikey_scope` to OCA after community feedback.

## Sources

- [Airtable PATs guide](https://airtable.com/developers/web/guides/personal-access-tokens)
- [Airtable scopes reference](https://airtable.com/developers/web/api/scopes)
- [Airtable PAT creation support](https://support.airtable.com/docs/creating-personal-access-tokens)
- Odoo Live Chat 2026-05-18 (Heather, Wei) — quote in ADR context
- [Odoo 19.0 `res.users.apikeys` source](https://github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/res_users.py)
