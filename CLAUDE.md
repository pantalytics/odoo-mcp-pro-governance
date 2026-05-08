# Claude Code Context

Project context for Claude Code AI assistant working in this repo.

## Module Overview

**pan_mcp_pro_governance** — Free €0 companion app to **MCP Pro**, the AI connector for Odoo. Distributed via Odoo App Store under the listing name "MCP Pro".

The actual MCP server (which connects Odoo to Claude/ChatGPT/Cursor/Gemini) runs *outside* Odoo — see [odoo-mcp-pro](https://github.com/pantalytics/odoo-mcp-pro) (open source) and the hosted SaaS at `pantalytics.com/apps/odoo-mcp-server`. This addon installs *inside* the customer's Odoo and is the operator-facing visibility/oversight surface.

For the full three-repo family map see [docs/research/07_related_repos.md](docs/research/07_related_repos.md).

## Models

| Model | Purpose | Mutability |
|---|---|---|
| `mcp.governance.agent.identity` | First-class identity for every AI agent that talks to Odoo | mutable lifecycle (draft/active/suspended/revoked) |
| `mcp.governance.audit.log` | ORM-level audit trail (per-record CRUD) | append-only |
| `mcp.governance.api.call.log` | Per-HTTP-request log of inbound MCP calls | append-only |

The two append-only models raise `AccessError` from `write` and `unlink` — even managers cannot tamper. Correlation between them is via `x_request_id`.

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
x_agent_identity_id = fields.Many2one(...)
x_request_id = fields.Char(...)
x_tool_name = fields.Char(...)
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
| `models/agent_identity.py` | Agent identity model + lifecycle actions |
| `models/audit_log.py` | Append-only ORM audit log |
| `models/api_call_log.py` | Append-only per-HTTP-request log + audit log correlation |
| `views/mcp_governance_*_views.xml` | Tree/form/search per model |
| `views/mcp_governance_menus.xml` | Top-level menu "MCP Pro" + submenus |
| `security/mcp_pro_governance_groups.xml` | User / Manager groups |
| `security/ir.model.access.csv` | Per-model ACLs |
| `tests/test_*.py` | Unit tests (TransactionCase) |
| `static/description/index.html` | App Store listing HTML (do not put external links here) |
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
make test-one TAG=:TestApiCallLog.test_audit_log_correlation
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

- This app is €0, LGPL-3, listed under name "MCP Pro" on Odoo App Store
- `static/description/index.html` allows ONLY `mailto:` and YouTube canonical anchors. **No `https://pantalytics.com` anchors** in listing HTML.
- The in-app CTA promoting the MCP Pro SaaS lives in a single discreet menu item (planned: Configuration → About) — not banners on every view.
- Manifest must drop "promised future features" before submission — reviewers flag those as misleading.
- Always test fresh-DB install: `make test` on a new container — failed install = top App Store takedown trigger.

See [.claude memory](docs/research/07_related_repos.md) and `~/.claude/projects/.../memory/` for full positioning decisions.
