# Claude Code Context

Project context for Claude Code AI assistant working in this repo.

## Module Overview

**pan_mcp_pro_governance** — Free €0 companion app to **MCP Pro**, the AI connector for Odoo. Distributed via Odoo App Store under the listing name "MCP Pro".

The actual MCP server (which connects Odoo to Claude/ChatGPT/Cursor/Gemini) runs *outside* Odoo — see [odoo-mcp-pro](https://github.com/pantalytics/odoo-mcp-pro) (open source) and the hosted SaaS at `pantalytics.com/apps/odoo-mcp-server`. This addon installs *inside* the customer's Odoo and is the operator-facing visibility/oversight surface.

For the full three-repo family map see [docs/research/07_related_repos.md](docs/research/07_related_repos.md).

## Design & Feedback

- **UI design rules** for this module: [docs/dev/design.md](docs/dev/design.md). Bound to Pantalytics design philosophy at [brand.pantalytics.com/en/design-philosophy](https://brand.pantalytics.com/en/design-philosophy). Touching menus/views/forms? Read it first.
- **Feedback loops** for "how do I know my change is good?": [docs/dev/FEEDBACK.md](docs/dev/FEEDBACK.md). Lists every loop from pre-commit (<2s) to CI (~6 min) and which to use when.
- **Documentation workflow**: [docs/README.md](docs/README.md). `docs/user/` is the master for end-user help (one-way sync → Odoo Knowledge); `docs/dev/` stays GitHub-only. No docs on pantalytics.com.

## What this module actually does

Two product surfaces, two dependencies. Almost all of v0.4 is `_inherit`
overrides on existing Odoo / OCA models, not new models.

**Surface 1 — scoped API keys** (added in v0.3, hardened in v0.4):
- Each `res.users.apikeys` row can bind to a single `res.users.role`
  via `x_role_id`. State (`x_state` = active / suspended / revoked) +
  observability fields (`x_last_used`, `x_use_count`).
- During a request authenticated by a role-bound key, the user's
  effective groups are narrowed to the role's groups.
- Narrowing is at the source: `res.users._get_group_ids` and
  `res.users._compute_all_group_ids`. Cache-bypassing overrides on
  `ir.model.access._get_allowed_models` and `ir.rule._compute_domain`
  ensure the narrowing reaches every consumer.
- Both `/json/2/*` (modern bearer) and `/jsonrpc` (legacy) routes go
  through our `_check_credentials` override. Thread-local fallback for
  legacy path; `ir.http._dispatch` clears it per request.

**Surface 2 — audit log** (added in v0.2):
- Reuses OCA `auditlog` (vendored as `pan_mcp_auditlog/` since v1.2.0
  — see ADR-013): `auditlog.http.request`, `auditlog.http.session`,
  `auditlog.log`, `auditlog.log.line`. Model technical names unchanged
  from upstream; only the module slug was renamed for the App Store.
- `post_init_hook` in [hooks.py](pan_mcp_pro_governance/hooks.py) seeds
  draft `auditlog.rule` records for sale.order, res.partner,
  account.move, crm.lead, product.template, stock.picking — only for
  models whose owning module is installed.

**Parked for a later release** (model stays in codebase, menu hidden
behind `base.group_no_one`):
- `mcp.governance.agent.identity` — first-class identity model with
  provider, owner, lifecycle. Available in developer mode for early
  adopters; not surfaced in the default UI.

**Dropped in v0.2:** `mcp.governance.audit.log` and
`mcp.governance.api.call.log` from v0.1. The migration in
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
| `models/res_users.py` | `_get_group_ids` and `_compute_all_group_ids` overrides — the source of narrowing. Plus `_get_api_key_role()` helper that reads role-id from session + thread-local. |
| `models/res_users_apikeys.py` | Adds `x_role_id`, `x_state`, `x_last_used`, `x_use_count` to the native API key model. Overrides `_check_credentials` to stash role-id on both session and thread-local. Manages a per-thread storage in `_mcp_thread_local`. |
| `models/res_users_apikeys_description.py` | Wizard inherit: adds the optional Role dropdown filtered to the user's own roles. Carries the role over to the freshly-generated key in `make_key`. |
| `models/ir_model_access.py` | Bypasses parent's ormcache(uid, mode) when an API-key role is active, then re-runs the same SQL with the narrowed group ids. Plus `_make_access_error` rewrite for clearer role-context messages. |
| `models/ir_rule.py` | Adds `_mcp_api_key_role_id` to `_compute_domain_keys` so the rule-domain cache differentiates per role. Threads the role id through `env.context` during a narrowed call. |
| `models/ir_http.py` | Resets the API-key role thread-local at the start of every request so a UI session that follows an API-key request on the same worker thread is not inadvertently narrowed. |
| `models/agent_identity.py` | The parked first-class agent identity model. Menu hidden behind `base.group_no_one` in v0.4; lives on for future v0.5+ work. |
| `hooks.py` | `post_init_hook` seeds draft `auditlog.rule` rows for installed AI-target models. |
| `migrations/19.0.0.2.0/pre-migration.py` | Drops the two v0.1 governance log tables on upgrade. |
| `views/mcp_governance_apikeys_views.xml` | The API key wizard inherits (Role dropdown), the kanban inherit (shows role + state + use count), the show-form inherit (rewrites the "full access" warning), and the top-level "API Keys" act_window for the MCP Pro menu. |
| `views/mcp_governance_api_call_log_views.xml` | Window action over `auditlog.http.request` re-using OCA's views. |
| `views/mcp_governance_agent_identity_views.xml` | Tree/form/search/action for the parked agent identity model. |
| `views/mcp_governance_menus.xml` | Top-level "MCP Pro" + Audit Log + API Keys (+ hidden Agent Identities) + Configuration → Audit Rules. |
| `security/mcp_pro_governance_groups.xml` | User / Manager groups; imply `pan_mcp_auditlog.group_auditlog_*`. |
| `security/ir.model.access.csv` | ACL rows for `mcp.governance.agent.identity` only. |
| `tests/test_*.py` | Unit tests (TransactionCase) + web tours. |
| `static/description/index.html` | App Store listing HTML (no external links allowed). |
| `static/src/js/tours/` | Web tours for HttpCase tests. |

## Local Docker setup

Each addon repo has its own `.local/` (gitignored) with `docker-compose.yml` + `odoo.conf`. A shared Dockerfile lives at `~/Documents/GitHub/.docker/Dockerfile` and Enterprise source at `~/Documents/GitHub/odoo-enterprise/`.

```
~/Documents/GitHub/
├── .docker/Dockerfile                ← Shared image (Enterprise + deps)
├── odoo-enterprise/                  ← Odoo 19 Enterprise source
└── odoo-mcp-pro-governance/          ← Bundle: 3 sibling addon folders
    ├── pan_mcp_auditlog/             ← Vendored OCA auditlog (renamed)
    ├── pan_mcp_user_role/            ← Vendored OCA base_user_role (renamed)
    ├── pan_mcp_pro_governance/       ← The governance addon proper
    └── .local/                       ← This repo's dev config (gitignored)
        ├── docker-compose.yml        ← bind-mounts the repo root
        └── odoo.conf
```

No separate OCA clones needed since v1.2.0 — the two OCA addons are
bundled in this repo as `pan_mcp_auditlog/` and `pan_mcp_user_role/`.
If you previously had `oca-server-tools` and `oca-server-backend`
cloned as bind mounts, remove them from `docker-compose.yml` to avoid
model-name conflicts (the bundled folders and OCA originals both
declare `auditlog.rule`, `res.users.role`, etc.).

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
