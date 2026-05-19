# Roadmap

The module lands in thin vertical slices. Each slice is a real feature
you can demo; no slice ships half-wired.

## v0.1 — Scaffold *(2026-05-08, released)*

- [x] Module manifest, security groups, menus
- [x] `mcp.governance.agent.identity` model (CRUD + views)
- [x] `mcp.governance.audit.log` append-only log (CRUD + views, never
      populated in production — dropped in v0.2)
- [x] Smoke tests

## v0.2 — Audit log via OCA *(2026-05-18, released)*

- [x] Switch license LGPL-3 → AGPL-3 (ADR-001)
- [x] Depend on OCA `auditlog`; drop in-house log models (ADR-002, 003)
- [x] `post_init_hook` seeds draft audit rules for AI-target models
- [x] Agent identity gets smart-button into `auditlog.http.request`
- [x] End-to-end verified on production pantalytics.odoo.com

## v0.3 — Scoped API keys *(2026-05-19, released)*

- [x] Depend on OCA `base_user_role` (ADR-007 → 010)
- [x] `res.users.apikeys` gains `x_role_id`, `x_state`, `x_last_used`,
      `x_use_count`
- [x] Wizard adds optional Role dropdown filtered to the current
      user's roles (ADR-009 → 010)
- [x] One role per key, not many (ADR-011 — diverges from OCA's
      user-level stacking)
- [x] Soft default: leave the role empty and the key behaves like a
      standard Odoo key

## v0.4 — Security hardening *(2026-05-19, released)*

- [x] Narrow at the source: `res.users._get_group_ids` and
      `_compute_all_group_ids` return the role's groups when a role is
      in scope
- [x] Cache-bypass on `ir.model.access._get_allowed_models` and
      `ir.rule._compute_domain` so narrowing reaches every consumer
- [x] Both `/json/2/*` (modern bearer) and `/jsonrpc` (legacy)
      endpoints close the same narrowing — thread-local fallback for
      the legacy path
- [x] `ir.http._dispatch` clears the thread-local per request to
      prevent leakage to UI sessions on the same worker thread
- [x] Role-specific error message ("the role X does not allow
      `<op>` on `<model>`") replaces Odoo's generic "you need group Y"

## v0.5 — Agent identity surfaced (planned)

- [ ] Promote `mcp.governance.agent.identity` out of developer-mode
      visibility into the default menu
- [ ] Bind agent identity to API key (M2O) so the audit log can
      attribute calls to a named agent, not just a key id
- [ ] Lifecycle actions write to the audit log
- [ ] Block authentication for `res.users.apikeys` rows whose agent
      identity is suspended/revoked
- [ ] List view: provider, owner, last_seen, calls_today, state

## v0.6 — Audit depth (planned)

- [ ] Optional retention of prompt/response payloads with PII policy
- [ ] CSV / JSONL export for external SIEM
- [ ] Dashboard: calls per agent, top models touched, anomaly flags

## v0.7 — SoD and policy engine (planned)

- [ ] SoD conflict matrix (configurable pairs of incompatible
      permissions, e.g. create + approve PO)
- [ ] Detection report: which agents currently violate SoD
- [ ] Per-agent quotas and rate limits
- [ ] Approval workflow gate for high-impact actions

## v0.8 — Zitadel / OIDC SSO (optional add-on)

- [ ] Sub-module `mcp_pro_governance_sso_zitadel`
- [ ] Map Zitadel org → Odoo company, Zitadel role → Odoo group
- [ ] JIT provisioning of agent identities from Zitadel service users

## v1.0 — Odoo App Store release (EU AI Act deadline 2026-08-02)

- [ ] Translations (NL, EN, DE, FR)
- [ ] `static/description/index.html` polished for app store
- [ ] End-to-end docs and screencasts
- [ ] Installable on a fresh Odoo 19 without touching `odoo.conf`
- [ ] EU AI Act Art. 13 transparency mapping: which agents touch which
      models, with named accountability
