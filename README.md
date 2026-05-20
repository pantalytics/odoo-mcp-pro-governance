# MCP Pro Governance

Free €0 companion to **MCP Pro**, the AI connector for Odoo. Installs
*inside* your Odoo and gives operators **scoped API keys bound to user
roles**, plus a full audit trail of every inbound call. Built on OCA
`auditlog` and OCA `base_user_role`.

**[Full documentation](https://pantalytics.gitbook.io/pantalytics-docs/)** (coming)

## Features

**Scoped API keys** (`res.users.apikeys` + OCA `base_user_role`):
- Bind each API key to a single OCA user role
- During a request authenticated by that key, the user's effective
  permissions are exactly the role's groups — never broader than the
  owning user, never broader than the role
- Works with both modern (`/json/2/*` bearer) and legacy (`/jsonrpc`)
  endpoints
- Suspended / revoked keys fail closed at authentication
- Last-used timestamp and call counter per key
- Optional: leave the role empty and the key inherits the user's full
  permissions (standard Odoo behaviour)

**Audit log** (powered by OCA `auditlog`):
- One row per inbound HTTP request from any audited user — path,
  status, duration, request id, session id
- Per-record ORM change log correlated to the originating call via
  `http_request_id`
- Pre-seeded draft rules for `sale.order`, `res.partner`, `account.move`,
  `crm.lead`, `product.template`, `stock.picking` — created only for
  modules already installed in the database
- Operator activates rules in Settings → Audit (OCA) or
  MCP Pro → Configuration → Audit Rules

**Security groups:**
- MCP Pro User (read-only; implies `auditlog.group_auditlog_user`)
- MCP Pro Manager (administration; implies `auditlog.group_auditlog_manager`)

**On the roadmap:**
- Agent identity registry surfaced in UI (model exists, hidden in
  developer mode for now)
- Per-agent policies, quotas, risk classification
- Approval workflows for high-impact actions
- EU AI Act compliance reporting

See [ROADMAP.md](ROADMAP.md) for the full plan and the
[ADR folder](docs/adr/) for the architecture decisions behind every
choice.

---

## Why this module?

Standard Odoo was designed for humans clicking through forms. When an
AI agent fires 5,000 actions per hour against the same user account,
the gaps show. API keys inherit the full permissions of their owning
user — there is no built-in way to scope them. Audit trails record
field changes, not which prompt or agent drove the decision. And
Odoo's per-user billing makes "one technical user per agent" too
expensive to recommend.

This module fills those gaps with thin, well-bounded primitives. It
does not replace Odoo's ACLs — it instruments around them.

> "AI doesn't change the rules of your ERP. It changes the speed."
> [AI in ERP: a practical guide](https://pantalytics.com/en/post/ai-in-erp-practical-guide)

The forcing function for v1: EU AI Act Art. 26 (deployer obligations),
Art. 12 (record-keeping), Art. 13 (transparency) and Art. 50 all
become applicable on **2026-08-02**. The roadmap is scoped to deliver
a defensible module by that date. See [docs/research/synthesis.md](docs/research/synthesis.md)
for the full design rationale.

---

## Installation

From v0.5.0 onwards this repository ships its two OCA dependencies
**bundled** at the root: `auditlog/` (OCA `server-tools` 19.0.1.0.1) and
`base_user_role/` (OCA `server-backend` 19.0.1.0.2). One install, all
three addons appear in your Apps menu. See [NOTICE.md](NOTICE.md) for
attribution and [ADR-012](docs/adr/012-vendor-oca-dependencies.md) for
why the vendoring is necessary on apps.odoo.com.

### Via apps.odoo.com (default)

Search **MCP Pro** → **Install on Odoo.sh** (or download the tarball
and install via your usual route). Odoo auto-installs `auditlog` and
`base_user_role` from the same package because they sit alongside in
the upload.

### As Git submodule (Odoo.sh)

```bash
git submodule add -b 19.0 git@github.com:pantalytics/odoo-mcp-pro-governance.git addons/pan_mcp_pro_governance_repo
# The repo contains three sibling module folders; point Odoo.sh's
# addons_path at the repo root so all three are picked up.
git commit -m "Add MCP Pro Governance bundle (3 addons)"
git push
```

### Standalone

```bash
git clone -b 19.0 git@github.com:pantalytics/odoo-mcp-pro-governance.git
# Add the repo root to your Odoo addons path. The three sibling
# folders (auditlog, base_user_role, pan_mcp_pro_governance) all
# become installable.
```

Then in Odoo: **Apps → Update Apps List → install "MCP Pro"**.

Requires Odoo 19.0 and Python 3.11+. No separate OCA install required.

### Using your own OCA copies instead

If you already have the OCA originals on a different addons-path entry
(e.g. via your own Odoo.sh submodule of `OCA/server-tools`), Odoo's
first-match resolution uses those — you can ignore our bundled copies
or even remove them after install.

---

## Setup

After installing, define a role and create a scoped key.

1. **Define roles** at Settings → Users & Companies → User Roles. A
   role is a named bundle of `res.groups`. For an AI agent that only
   needs to read contacts, pick `Contact Creation` in the Groups tab
   and nothing else. The transitive group expansion gives the role
   exactly what it implies — nothing more.

2. **Assign the role** to whichever user the integration logs in as
   (could be your own admin user; you don't need a separate billable
   user per agent). Settings → Users → user form → Roles tab.

3. **Create the API key** with the role attached. Settings → Users →
   user form → Account Security → Add API Key. The wizard shows a
   "Role (optional)" dropdown filtered to the roles assigned to your
   user. Pick one and click Generate.

4. **Use the key** from your AI agent / cron / n8n / etc. as the
   bearer token. The key's effective permissions during every call
   will be exactly the role's groups, not your user's full permissions.

5. **Audit Rules** (manager only): MCP Pro → Configuration → Audit
   Rules. Six draft rules are pre-seeded for AI-action target models.
   Open each, optionally restrict `Users` to the technical user, and
   click Subscribe to confirm. Until subscribed, rules log nothing.

---

## Security

| Aspect | Implementation |
|--------|----------------|
| Permission narrowing | Role-bound key sees only role's groups. Enforced at `res.users._get_group_ids` (source of truth) plus cache-bypass overrides on `ir.model.access._get_allowed_models` and `ir.rule._compute_domain`. Covers `has_group`, model ACLs and record rules. |
| Key state | active / suspended / revoked. Suspended and revoked keys fail closed at authentication. |
| Auth paths | Both `/json/2/*` (modern bearer) and `/jsonrpc` (legacy) paths route through our `_check_credentials` override. |
| Cross-request isolation | Thread-local cleared at the start of every request (via `ir.http._dispatch`), so a UI session that follows an API-key request on the same worker thread does not inherit the narrowed role. |
| Audit log mutability | Provided by OCA `auditlog`. Logs are append-only by convention; cleanup is opt-in via auditlog's autovacuum cron. |
| Data residency | No call-home, no telemetry, everything stays in your DB. |

Known scope limit: code that reads `user.group_ids` directly (without
going through `_get_group_ids` or `all_group_ids`) is not narrowed.
Core Odoo and most addons go through the narrowed methods; a small
number of third-party addons may not. `sudo()` remains Odoo's
standard escape hatch and is not closed by this module.

See [docs/research/](docs/research/) for the full research corpus —
Microsoft reference architecture, standards and EU AI Act, Odoo
internals, MCP ecosystem, real incidents, competitive landscape,
synthesis. See [docs/adr/](docs/adr/) for the 11 architecture
decisions that shaped what's in this module today.

---

## Related projects

- [odoo-mcp-pro](https://github.com/pantalytics/odoo-mcp-pro) — MCP
  server exposing Odoo to AI agents.
- [odoo-mcp-pro-admin](https://github.com/pantalytics/odoo-mcp-pro-admin) —
  hosted admin panel (proprietary SaaS layer).
- [OCA/server-tools `auditlog`](https://github.com/OCA/server-tools/tree/19.0/auditlog) —
  required dependency; provides the HTTP request log and per-record
  audit trail.
- [OCA/server-backend `base_user_role`](https://github.com/OCA/server-backend/tree/19.0/base_user_role) —
  required dependency; provides the role model that scoped keys bind
  to.

---

## Development

### Running tests

```bash
docker-compose run --rm odoo python -m odoo -c /etc/odoo/odoo.conf \
  -d test_db -u pan_mcp_pro_governance --test-enable \
  --test-tags=pan_mcp_pro_governance --stop-after-init
```

### Code style

Ruff, line length 100, double quotes. Run `pre-commit run --all-files`
before pushing. Matches sibling MCP Pro repos.

---

## License

AGPL-3 (from v0.2.0, switched from LGPL-3 when depending on OCA
`auditlog`). See [LICENSE](LICENSE).

Pantalytics B.V. — support@pantalytics.com
