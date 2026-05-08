# MCP Pro Governance

Data and AI governance for Odoo - agent identities, scoped MCP keys,
append-only audit. Companion module to MCP Pro.

**[Full documentation](https://pantalytics.gitbook.io/pantalytics-docs/)** (coming)

## Features

**Agent identities:**
- First-class model for every AI agent that touches your data
- Owner, sponsor, provider, lifecycle state
- Shadow `res.users` binding so Odoo ACLs still apply
- Last-seen tracking

**Append-only audit log:**
- Every agent action writes an immutable row
- Agent identity, acting user, action, model, record, request id, prompt hash
- Write and unlink raise `AccessError` - no exceptions

**Security groups:**
- MCP Governance User (read-only)
- MCP Governance Manager (administration)

**On the roadmap:**
- Scoped keys with expiry and rate limits (v0.3)
- Lethal-trifecta policy engine (v0.3)
- AI system card per agent, EU AI Act Art. 13 (v0.4)
- Hash-chained audit, incident register, DPIA template (v0.5)

See [ROADMAP.md](ROADMAP.md) for the full plan.

---

## Why this module?

Standard Odoo was designed for humans clicking through forms. When an
AI agent fires 5,000 actions per hour against the same user account,
the gaps show - no first-class agent identity, API keys with full
user permissions, audit depth that does not capture the prompt that
drove the decision.

This module fills those gaps with thin, well-bounded primitives. It
does not replace Odoo's ACLs - it instruments around them.

> "AI doesn't change the rules of your ERP. It changes the speed."
> [AI in ERP: a practical guide](https://pantalytics.com/en/post/ai-in-erp-practical-guide)

The forcing function for v1: EU AI Act Art. 26 (deployer obligations),
Art. 12 (record-keeping), Art. 13 (transparency) and Art. 50 all
become applicable on **2026-08-02**. The roadmap is scoped to deliver
a defensible module by that date. See [docs/research/synthesis.md](docs/research/synthesis.md)
for the full design rationale.

---

## Installation

### As Git Submodule (Odoo.sh)

1. In Odoo.sh, go to **Settings -> Submodules**
2. Click **Add submodule**
3. Enter: `git@github.com:pantalytics/odoo-mcp-pro-governance.git`
4. Copy the **Public Key** and add it as Deploy Key in GitHub

```bash
# Local: add submodule
git submodule add git@github.com:pantalytics/odoo-mcp-pro-governance.git addons/pan_mcp_pro_governance
git commit -m "Add pan_mcp_pro_governance submodule"
git push
```

### Standalone

```bash
git clone git@github.com:pantalytics/odoo-mcp-pro-governance.git
# Add the inner pan_mcp_pro_governance/ directory to your Odoo addons path.
```

Then in Odoo: **Apps -> Update Apps List -> install "MCP Pro Governance"**.

Requires Odoo 19.0, Python 3.11+. No external Python dependencies for the
base module.

---

## Setup

After installing, go to **Governance** (top-level menu).

1. **Agent Identities** - register every AI agent that talks to this
   Odoo instance. Name, provider, owner, technical user.
2. **Audit Log** - read-only stream of agent activity. Populated by
   MCP Pro or any integration writing to `mcp.governance.audit.log`.
3. **Configuration** (manager only) - security group assignments.

---

## Security

| Aspect | Implementation |
|--------|----------------|
| Audit mutability | Append-only; `write()` and `unlink()` raise `AccessError` |
| Audit insertion | Restricted to `base.group_system` (the MCP server's tech user). Module User/Manager groups are read-only on audit and API call logs — they cannot inject false rows from the UI. |
| Agent lifecycle | draft / active / suspended / revoked; revocation is permanent |
| Access control | Two groups (User, Manager); no record rules yet — both see all rows. Use Odoo native ACLs / multi-company for finer scoping. |
| Data residency | No call-home, no telemetry, everything stays in your DB |

See [docs/research/](docs/research/) for the full research corpus -
Microsoft reference architecture, standards and EU AI Act, Odoo
internals, MCP ecosystem, real incidents, competitive landscape,
synthesis.

---

## Related projects

- [odoo-mcp-pro](https://github.com/pantalytics/odoo-mcp-pro) - MCP
  server exposing Odoo to AI agents.
- [odoo-mcp-pro-admin](https://github.com/pantalytics/odoo-mcp-pro-admin) -
  hosted admin panel (proprietary SaaS layer).
- [pan_outlook_pro](https://github.com/pantalytics/pan_outlook_pro) -
  Microsoft 365 email integration.
- OCA [`base_user_role`](https://github.com/OCA/server-auth/tree/19.0/base_user_role) -
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

LGPL-3. See [LICENSE](LICENSE).

Pantalytics B.V. - support@pantalytics.com
