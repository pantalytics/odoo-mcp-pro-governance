# MCP Pro Governance

Free €0 companion to **MCP Pro**, the AI connector for Odoo. Installs
*inside* your Odoo and gives operators a first-class registry of every AI
agent plus an audit trail of every inbound call. Built on OCA `auditlog`.

**[Full documentation](https://pantalytics.gitbook.io/pantalytics-docs/)** (coming)

## Features

**Agent identities** (`mcp.governance.agent.identity`):
- First-class model for every AI agent that touches your data
- Owner, provider, lifecycle state (draft / active / suspended / revoked)
- Bound to a technical `res.users` so Odoo ACLs still apply
- Smart-button link to every API call this agent has made

**API call log** (powered by OCA `auditlog`):
- One row per inbound HTTP request from any audited user — path, status,
  duration, request id
- Per-record ORM change log correlated to the originating call
- Pre-seeded draft rules for `sale.order`, `res.partner`, `account.move`,
  `crm.lead`, `product.template`, `stock.picking` — created only for
  modules that are already installed

**Security groups:**
- MCP Pro User (read-only; implies `auditlog.group_auditlog_user`)
- MCP Pro Manager (administration; implies `auditlog.group_auditlog_manager`)

**On the roadmap:**
- Scoped keys with expiry and rate limits (v0.3)
- Lethal-trifecta policy engine (v0.3)
- AI system card per agent, EU AI Act Art. 13 (v0.4)
- Hash-chained audit, incident register, DPIA template (v0.5)

See [ROADMAP.md](ROADMAP.md) for the full plan and
[docs/research/08_api_call_logging_options.md](docs/research/08_api_call_logging_options.md)
for the v0.2 architecture rationale.

---

## Why this module?

Standard Odoo was designed for humans clicking through forms. When an
AI agent fires 5,000 actions per hour against the same user account,
the gaps show — no first-class agent identity, API keys with full
user permissions, audit depth that does not capture the prompt that
drove the decision.

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

Pulls in OCA `auditlog` as a dependency. Either install both modules
from the Odoo App Store, or add `OCA/server-tools` (branch `19.0`) to
your addons path alongside this repo.

### As Git submodule (Odoo.sh)

1. In Odoo.sh, go to **Settings → Submodules**
2. Add this repo and `OCA/server-tools` (branch `19.0`) as submodules
3. Install **MCP Pro** from the Apps menu — Odoo pulls in `auditlog` automatically

```bash
# Local: add submodules
git submodule add git@github.com:pantalytics/odoo-mcp-pro-governance.git addons/pan_mcp_pro_governance
git submodule add -b 19.0 https://github.com/OCA/server-tools.git addons/oca-server-tools
git commit -m "Add MCP Pro Governance + OCA server-tools submodules"
git push
```

### Standalone

```bash
git clone git@github.com:pantalytics/odoo-mcp-pro-governance.git
git clone -b 19.0 https://github.com/OCA/server-tools.git
# Add `pan_mcp_pro_governance/` and `server-tools/auditlog/` to your Odoo addons path.
```

Then in Odoo: **Apps → Update Apps List → install "MCP Pro"**.

Requires Odoo 19.0, Python 3.11+, and OCA `auditlog` 19.0.

---

## Setup

After installing, open **MCP Pro** (top-level menu).

1. **Agent Identities** — register every AI agent that talks to this
   Odoo instance. Pick the technical Odoo user the MCP server logs in
   as — that binding is what links the agent to its API calls.
2. **API Call Log** — read-only stream of inbound HTTP requests. Each
   row links down to per-record ORM changes.
3. **Configuration → Audit Rules** (manager only) — six draft rules are
   created on install. Open each rule, optionally restrict `Users` to
   the MCP technical user, and click **Subscribe** to confirm it. Until
   subscribed, rules do nothing.

---

## Security

| Aspect | Implementation |
|--------|----------------|
| Audit log mutability | Provided by OCA `auditlog`. Logs are append-only by convention; cleanup is opt-in via auditlog's autovacuum cron. |
| Agent lifecycle | draft / active / suspended / revoked; revocation is permanent |
| Access control | Two groups (User, Manager) that imply the OCA `auditlog` groups. No record rules yet — both see all rows. Use Odoo native ACLs / multi-company for finer scoping. |
| Data residency | No call-home, no telemetry, everything stays in your DB |

See [docs/research/](docs/research/) for the full research corpus —
Microsoft reference architecture, standards and EU AI Act, Odoo
internals, MCP ecosystem, real incidents, competitive landscape,
synthesis.

---

## Related projects

- [odoo-mcp-pro](https://github.com/pantalytics/odoo-mcp-pro) — MCP
  server exposing Odoo to AI agents.
- [odoo-mcp-pro-admin](https://github.com/pantalytics/odoo-mcp-pro-admin) —
  hosted admin panel (proprietary SaaS layer).
- [OCA/server-tools `auditlog`](https://github.com/OCA/server-tools/tree/19.0/auditlog) —
  required dependency; provides the HTTP request log and per-record audit trail.
- OCA [`base_user_role`](https://github.com/OCA/server-auth/tree/19.0/base_user_role) —
  role management; this module will integrate with, not replace.

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
