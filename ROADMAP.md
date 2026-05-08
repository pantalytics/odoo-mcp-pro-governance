# Roadmap

The module lands in thin vertical slices. Each slice is a real feature
you can demo; no slice ships half-wired.

## v0.1 — Scaffold (current)

- [x] Module manifest, security groups, menus
- [x] `mcp.governance.agent.identity` model (CRUD + views)
- [x] `mcp.governance.audit.log` append-only log (CRUD + views)
- [x] Smoke tests

## Pre-v0.2 — notes before writing code

- Check whether `auth_jwt` (OCA/server-auth) has a 19.0 branch yet;
  if not, decide upstream port vs minimal vendored verifier.
- Resolve the `env.agent_uid` thread-local spike (see
  [synthesis §11](docs/research/synthesis.md)).
- Legal review on retention reconciliation and
  provider-vs-deployer threshold.

## v0.2 — Agent identities in practice

- [ ] Link agent identity to `res.users` (technical user) with lifecycle
      state (draft / active / suspended / revoked)
- [ ] Lifecycle actions write to the audit log
- [ ] Block login for `res.users` backing a suspended/revoked identity
- [ ] List view: last_seen, calls_today, state

## v0.3 — Scoped API / MCP keys

- [ ] `mcp.governance.key.scope` model (read:model, write:model,
      execute:server_action, ...)
- [ ] Extend `res.users.apikeys` with `scope_ids` and `agent_identity_id`
- [ ] Enforcement hook — reject calls outside declared scopes
- [ ] Key rotation tracking and expiry

## v0.4 — Audit depth

- [ ] Capture `request_id`, `prompt_hash`, `tool_name` on every MCP call
- [ ] Optional retention of prompt/response payloads with PII policy
- [ ] CSV / JSONL export for external SIEM
- [ ] Dashboard: calls per agent, top models touched, anomaly flags

## v0.5 — SoD and RBAC integration

- [ ] Depend on OCA `base_user_role`
- [ ] SoD conflict matrix (configurable pairs of incompatible
      permissions, e.g. create+approve PO)
- [ ] Detection report: which agents currently violate SoD

## v0.6 — Zitadel / OIDC SSO (optional add-on)

- [ ] Sub-module `mcp_pro_governance_sso_zitadel`
- [ ] Map Zitadel org → Odoo company, Zitadel role → Odoo group
- [ ] JIT provisioning of agent identities from Zitadel service users

## v1.0 — Odoo App Store release

- [ ] Translations (NL, EN, DE, FR)
- [ ] `static/description/index.html` polished for app store
- [ ] End-to-end docs and screencasts
- [ ] Installable on a fresh Odoo 18 without touching `odoo.conf`
