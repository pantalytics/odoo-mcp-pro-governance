# Claude Code Context

Project context for Claude Code AI assistant working in this repo.

## Module Overview

**pan_mcp_pro_governance** — Free €0 companion app to **MCP Pro**, the AI connector for Odoo. Distributed via Odoo App Store under the listing name "MCP Pro".

The actual MCP server (which connects Odoo to Claude/ChatGPT/Cursor/Gemini) runs *outside* Odoo — see [odoo-mcp-pro](https://github.com/pantalytics/odoo-mcp-pro) (open source) and the hosted SaaS at `pantalytics.com/apps/odoo-mcp-server`. This addon installs *inside* the customer's Odoo and is the operator-facing visibility/oversight surface.

For the full three-repo family map see [docs/research/07_related_repos.md](docs/research/07_related_repos.md).

## Design & Feedback

- **UI design rules** for this module: [docs/design.md](docs/design.md). Bound to Pantalytics design philosophy at [brand.pantalytics.com/en/design-philosophy](https://brand.pantalytics.com/en/design-philosophy). Touching menus/views/forms? Read it first.
- **Feedback loops** for "how do I know my change is good?": [docs/FEEDBACK.md](docs/FEEDBACK.md). Lists every loop from pre-commit (<2s) to CI (~6 min) and which to use when.

## Models

| Model | Purpose | Mutability |
|---|---|---|
| `mcp.governance.agent.identity` | First-class identity for every AI agent that talks to Odoo | mutable lifecycle (draft/active/suspended/revoked) |

The HTTP call log and the per-record audit trail come from OCA `auditlog`
(dependency since v0.2.0): `auditlog.http.request`, `auditlog.http.session`,
`auditlog.log`, `auditlog.log.line`. The agent identity binds to a
`res.users` via `x_user_id` and links to the OCA records through that user.
A `post_init_hook` in [hooks.py](pan_mcp_pro_governance/hooks.py) seeds
draft `auditlog.rule` records for sale.order, res.partner, account.move,
crm.lead, product.template, stock.picking — only for models whose owning
module is installed.

`mcp.governance.audit.log` and `mcp.governance.api.call.log` from v0.1
were dropped in v0.2.0; the migration in
`migrations/19.0.0.2.0/pre-migration.py` drops the empty tables.

## Development Principles

1. **Odoo 19 compatibility** — verify before every commit
2. **Minimal footprint** — stay close to standard Odoo
3. **Companion positioning** — never make this app *do* what the MCP server does; it observes and governs
4. **No call-home** — telemetry, auto-signup, external POSTs are forbidden by the App Store guidelines and our positioning
5. **Lean implementation** — prefer configuration over code, reuse Odoo native features

### Odoo 19 checklist (verify before commit)

- [ ] No `attrs` in views → use `invisible`, `readonly`, `required` directly
- [ ] No `numbercall` on cron jobs (deprecated)
- [ ] Stored computed fields have `@api.depends` decorator
- [ ] Use `groups` attribute for field access control
- [ ] XML ids follow pattern: `module_name.record_name`
- [ ] Bump version in `__manifest__.py` (format: `19.0.X.Y.Z`) when DB schema changes
- [ ] Custom fields use `x_` prefix (see Conventions)

## Conventions

### `x_` prefix on custom fields (Odoo.sh requirement)

All fields specific to this module's domain use the `x_` prefix. Examples:

```python
x_user_id = fields.Many2one(...)
x_provider = fields.Selection(...)
x_api_call_count = fields.Integer(...)
```

**Keep without prefix** (Odoo standard fields, override or reuse):

- `name`, `active`, `sequence`, `state`, `display_name`, `create_date`, `write_date`

When a field's semantic meaning is *new* to the domain (e.g. "the technical user the agent operates as"), prefix even if a similar standard name exists — write `x_user_id`, not `user_id`.

### Other conventions

- XML ids: `view_mcp_governance_<model>_<viewtype>` for views, `action_mcp_governance_<model>` for actions, `menu_mcp_governance_<area>` for menus
- Selection fields: lowercase keys, capitalized labels (`("anthropic", "Anthropic (Claude)")`)
- All custom models use `mcp.governance.*` dotted naming
- Tests: `TransactionCase` for ORM, `HttpCase` for tours
- Ruff: line length 100, double quotes, black-compatible

## Key Files

| File | Purpose |
|---|---|
| `models/agent_identity.py` | Agent identity model + lifecycle actions + smart-button into `auditlog.http.request` |
| `hooks.py` | `post_init_hook` seeds draft `auditlog.rule` rows for installed AI-target models |
| `migrations/19.0.0.2.0/pre-migration.py` | Drops the two v0.1 governance log tables on upgrade |
| `views/mcp_governance_agent_identity_views.xml` | Agent identity tree/form/search/action |
| `views/mcp_governance_api_call_log_views.xml` | Window action over `auditlog.http.request` (re-uses OCA views) |
| `views/mcp_governance_menus.xml` | Top-level "MCP Pro" + Agent Identities + API Call Log + Configuration → Audit Rules |
| `security/mcp_pro_governance_groups.xml` | User / Manager groups; imply `auditlog.group_auditlog_*` |
| `security/ir.model.access.csv` | ACL rows for `mcp.governance.agent.identity` only |
| `tests/test_*.py` | Unit tests (TransactionCase) |
| `static/description/index.html` | App Store listing HTML (no external links allowed) |
| `static/src/js/tours/` | Web tours for HttpCase tests |

## Local Docker setup

Each addon repo has its own `.local/` (gitignored) with `docker-compose.yml` + `odoo.conf`. A shared Dockerfile lives at `~/Documents/GitHub/.docker/Dockerfile` and Enterprise source at `~/Documents/GitHub/odoo-enterprise/`.

```
~/Documents/GitHub/
├── .docker/Dockerfile               ← Shared image (Enterprise + deps)
├── odoo-enterprise/                  ← Odoo 19 Enterprise source
└── odoo-mcp-pro-governance/
    └── .local/                       ← This repo's dev config (gitignored)
        ├── docker-compose.yml
        └── odoo.conf
```

Container filesystem:

```
/opt/odoo/odoo-enterprise/         ← COPIED into image (rebuild on Enterprise change)
/mnt/extra-addons/pan_mcp_pro_governance/  ← BIND MOUNT from host (live editing)
/var/lib/odoo/                     ← NAMED VOLUME (persistent filestore)
/etc/odoo/odoo.conf                ← BIND MOUNT
```

### First-time setup

```bash
make build       # rebuild image (only when Dockerfile changes)
make up          # start Odoo + Postgres in background
make install     # install module on a fresh DB named 'dev'
```

Then open <http://localhost:8069>, login `admin` / `admin`, DB `dev`.

### Inner loop

| What changed | What to do |
|---|---|
| Python (models, methods) | `--dev=all` auto-reloads — refresh browser |
| XML views | `--dev=all` reads from disk — refresh browser |
| Manifest, new field, ACL CSV, data XML | `make upgrade` |
| OWL JS / SCSS | hard refresh on `/web?debug=assets` |

### Common targets

```bash
make logs         # tail Odoo logs
make shell        # exec bash inside Odoo container
make restart      # restart Odoo (rare; --dev=all usually obviates this)
make upgrade      # apply schema/manifest changes (-u pan_mcp_pro_governance)
make test         # fresh DB + install + run all module tests
make test-one TAG=:TestAgentIdentity.test_lifecycle_transitions
make lint         # pre-commit on all files
make e2e          # Playwright screenshot capture (for App Store assets)
make clean        # drop test_* databases
```

## Common Tasks

### Adding a new field

1. Add `x_field_name = fields.X(...)` to the appropriate model
2. Add the field to the relevant view XML
3. Bump manifest version (`__manifest__.py`)
4. `make upgrade` to apply schema change
5. Refresh browser

### Adding a new model

1. Create `models/<name>.py`
2. Register in `models/__init__.py`
3. Create `views/mcp_governance_<name>_views.xml` (tree/form/search/action)
4. Add menu entry in `views/mcp_governance_menus.xml`
5. Add ACL rows in `security/ir.model.access.csv`
6. Register view file in `__manifest__.py` `data` list
7. Bump manifest version
8. `make upgrade`

### Adding a UI test (web_tour)

1. Write tour in `static/src/js/tours/<name>_tour.js` (registered via `registry.category("web_tour.tours").add(...)`)
2. Add file to manifest `assets` block (`web.assets_backend`)
3. Write `tests/test_<name>_tour.py` extending `HttpCase`, calling `self.start_tour(...)`
4. Tag with `@tagged('post_install', '-at_install')`
5. Run via `make test-one TAG=:TestNameTour`

## App Store positioning rules

- This app is €0, AGPL-3, listed under name "MCP Pro" on Odoo App Store. License is AGPL-3 from v0.2.0 because we depend on OCA `auditlog` (AGPL-3).
- `static/description/index.html` allows ONLY `mailto:` and YouTube canonical anchors. **No `https://pantalytics.com` anchors** in listing HTML.
- The in-app CTA promoting the MCP Pro SaaS lives in a single discreet menu item (planned: Configuration → About) — not banners on every view.
- Manifest must drop "promised future features" before submission — reviewers flag those as misleading.
- Always test fresh-DB install: `make test` on a new container — failed install = top App Store takedown trigger.

See [.claude memory](docs/research/07_related_repos.md) and `~/.claude/projects/.../memory/` for full positioning decisions.
