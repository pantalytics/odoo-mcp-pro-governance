# MCP Pro server & admin internals

Architectural snapshot of the two sibling repos this governance addon observes.
Captured 2026-05-18 — verify against the source repos before acting on
specifics (file paths, table names, plan limits all drift).

For positioning and the three-repo family map, see
[07_related_repos.md](07_related_repos.md).

## odoo-mcp-pro (OSS, Elastic 2.0)

Stateless MCP server exposing Odoo to AI agents (Claude / ChatGPT / Cursor /
Gemini). Python package `mcp_server_odoo`. Single-tenant when self-hosted,
multi-tenant when the admin overlay is mounted.

### Entry points

- `python -m mcp_server_odoo` → `mcp_server_odoo/__main__.py`
- Transports: `stdio` (default, for Claude Desktop / Code) or
  `streamable-http` (for remote / SaaS). Selected via
  `ODOO_MCP_TRANSPORT` env var or `--transport` flag.
- Env-driven config: `ODOO_URL` + `ODOO_API_KEY` for single-tenant;
  presence of `DATABASE_URL` flips into multi-tenant mode.

### Modules in `mcp_server_odoo/`

| Module | Role |
|---|---|
| `__main__.py` | CLI parsing, transport dispatch |
| `server.py` | `OdooMCPServer` — FastMCP app factory, OAuth wiring |
| `tools.py` | `OdooToolHandler` — the 12 MCP tools |
| `resources.py` | `OdooResourceHandler` — the 4 URI resources |
| `odoo_json2_connection.py` | JSON/2 client for Odoo 19+ (httpx, Bearer + `X-Odoo-Database` header) |
| `odoo_connection.py` | XML-RPC client for Odoo 14–18 (stdlib `xmlrpc.client`) |
| `connection_protocol.py` | Abstract interface both connection clients implement |
| `version_detect.py` | Auto-detect Odoo API version (JSON/2 vs XML-RPC) |
| `registry.py` | `ConnectionRegistry` — caches connections per `(sub, tenant)`, 30 min TTL (multi-tenant only) |
| `oauth.py` | `ZitadelTokenVerifier` — token introspection + caching, scope validation |
| `access_control.py` | `AccessController` — `check_access_rights` before each tool, 5 min cache |
| `config.py` | `OdooConfig` dataclass; env loading + validation |
| `usage.py` | Rate-limit / usage-tracking **stub** — full impl injected by admin overlay |
| `schemas.py` | Pydantic result models (`SearchResult`, `RecordResult`, …) |
| `error_handling.py` | Custom exceptions, error context |
| `performance.py` | Query timing, cache stats |
| `odoo_knowledge.py` | Odoo domain knowledge injected as MCP server instructions |

### Exposed tools (12)

`search_records`, `get_record`, `create_record`, `create_records`,
`update_record`, `update_records`, `delete_record`, `delete_records`,
`import_records` (idempotent upsert via external IDs, wraps Odoo `load()`),
`list_models`, `list_resource_templates`, `server_info`, `post_message`,
`set_binary_field`.

Batch tools cap at 1000 records.

### Exposed resources (URI templates)

- `odoo://{model}/record/{record_id}` — one record
- `odoo://{model}/search` — first 10 with defaults
- `odoo://{model}/count` — total record count
- `odoo://{model}/fields` — field metadata

### Auth

| Mode | How |
|---|---|
| Single-tenant (stdio / self-host) | `ODOO_API_KEY` env var; falls back to `ODOO_USER` + `ODOO_PASSWORD`. One key for all calls. |
| Multi-tenant (HTTP / SaaS) | OAuth 2.1 via Zitadel. Token introspected at `/oauth/v2/introspect`; `sub` + `org_id` + scopes extracted. `ConnectionRegistry.get_connection(sub, org_id)` looks up the tenant row, decrypts the Odoo API key, lazily builds an `OdooJSON2Connection`. |

Odoo ACLs remain the source of truth either way — `AccessController` only
gates tool execution; row-level filtering is Odoo's job.

### Scoped keys, rate limiting, multi-tenant hooks

- **Scopes**: OAuth scope validation (`required_scopes = ["openid"]` in
  `server.py`). Custom scopes (e.g. `odoo:read`, `odoo:write`) can be
  enforced via Zitadel; no fine-grained per-model scoping today.
- **Rate limits**: `await self.usage_tracker.check_rate_limit(sub)` runs
  before every tool. Public stub no-ops; admin overlay enforces.
- **Tenant tables** (Postgres, owned by admin): `tenants(id, name, slug,
  zitadel_org_id, odoo_url, odoo_db, api_version, is_active)` and
  `user_connections(id, zitadel_sub, email, tenant_id, odoo_api_key,
  is_active)` — UNIQUE on `(zitadel_sub, tenant_id)`.

## odoo-mcp-pro-admin (closed, FastAPI SaaS)

Overlay that turns the OSS package into a hosted multi-tenant service.
At Docker build time it copies `mcp_server_odoo_admin/` into
`site-packages/mcp_server_odoo/admin/` and replaces the stub `usage.py`
with the real implementation.

### Bootstrap

- `mcp_server_odoo_admin/app.py` → `create_admin_app()` is a FastAPI
  factory that mounts `/admin`, `/billing`, `/login` onto the FastMCP
  Starlette app. Jinja2 templates, static files, PostHog + version
  globals injected here.
- Local dev: `bash local-dev.sh link` symlinks the admin module into the
  peer-installed public package for editable builds.
- Prod: Dockerfile multi-stage, runs as unprivileged `appuser` (UID 1000).
  Entrypoint stays `python -m mcp_server_odoo`.

### Modules in `mcp_server_odoo_admin/`

| Module | Role |
|---|---|
| `app.py` | App factory, route registration, template rendering |
| `auth.py` | Zitadel OIDC + PKCE; signed session cookies (8h); CSRF; dev-bypass via `ADMIN_DEV_LOGIN` |
| `db.py` | `DatabaseManager` (asyncpg pool); schema migrations; CRUD on `user_connections`, `teams`, `invites`, `usage_log`, `usage_daily`, `billing_records`, `usage_plans` |
| `routes.py` | Setup wizard, team management, connection profiles, invite acceptance |
| `billing.py` | Stripe Checkout sessions, Customer Portal links, webhook handler |
| `odoo_sync.py` | Scheduled cron: pushes Zitadel users + Stripe subscriptions into Pantalytics' own Odoo CRM (not the customer's) |
| `encryption.py` | Fernet (AES-128) for Odoo API keys at rest; falls back to plaintext with warning if `API_KEY_ENCRYPTION_KEY` unset |
| `usage.py` (overlay) | `UsageTracker`: in-memory rate-limit cache, fire-and-forget usage logging, optional PostHog events, `SessionLifecycleMiddleware` |

### Auth flow (Zitadel OIDC + PKCE)

1. `/login` → redirect to Zitadel authorize endpoint with PKCE
   (`code_challenge`, `code_verifier` stashed in `pending_auth` table).
2. `/login/callback` validates code, exchanges for ID token.
3. `sub` + `email` extracted, `user_connections` upserted.
4. Signed session cookie (`SESSION_COOKIE`, HttpOnly, SameSite=Lax)
   carries `{sub, email}`.
5. `@require_login` decorator gates routes.

Identity cardinality:

- Zitadel user (`zitadel_sub`) **1:1** `user_connections`
- `user_connections` **1:1 or NULL** `stripe_customer_id` (free = NULL)
- One Zitadel org per customer team — flat, no hierarchy.

### Plans & billing

| Plan | Calls/day | Price | Trial |
|---|---|---|---|
| Free | 50 | — | — |
| Pro | 500 | €25/user/mo | 30 days |
| Max | 10 000 | €100/user/mo | — |

Source of truth: `usage_plans` Postgres table (seeded on schema init)
plus `price.metadata.internal_plan` in Stripe (`free` / `pro` / `max`).

Billing endpoints:

- `GET /billing` — current plan, usage bar, upgrade links
- `POST /billing/checkout` — Stripe Checkout session
- `GET /billing/portal` — Stripe Customer Portal
- `POST /webhooks/stripe` — signature-verified; handles
  `customer.subscription.updated` / `.deleted`; invalidates the
  usage-tracker cache so new limits apply immediately (no UTC-midnight
  wait).

### Usage tracking

`UsageTracker` (in the overlay `usage.py`):

- `check_rate_limit(zitadel_sub)` reads `usage_daily` for today;
  in-memory cache `{sub: (date, count, limit)}` avoids a DB roundtrip
  per call.
- Fire-and-forget async inserts into `usage_log` (tool name, duration,
  error flag) and bumps `usage_daily`.
- Optional PostHog events (`tool_called`, `rate_limit_exceeded`) when
  `POSTHOG_API_KEY` is set; includes `plan_name`, `stripe_status`, `email`.

### Deployment

`deploy/deploy.sh` — blue/green:

1. Detect running slot (`mcp-blue` or `mcp-green`).
2. Build new image on the opposite slot.
3. Start new container, wait ≤ 30s for health check.
4. Drain old container 30s.
5. Kill old container.

Nginx/Caddy routes traffic; health probed via container inspect.

## Where this governance addon fits

- Runs **inside** the customer's Odoo; reads the audit trail produced
  by OCA `auditlog` (HTTP request log + per-record ORM log).
- Writes nothing to the SaaS stack; reads nothing from Zitadel or
  Stripe. Zero call-home — App Store rule.
- For v0.3 scoped keys, align field names with `mcp_server_odoo.*` so
  the server can enforce scopes per call. See
  [07_related_repos.md](07_related_repos.md) "Cross-references".
