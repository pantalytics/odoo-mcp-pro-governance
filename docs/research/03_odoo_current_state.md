# 03 — Current State of Data + AI / Auth / Audit / Access Primitives in Odoo

**Scope:** Odoo Community, Enterprise, and OCA (Odoo Community Association) modules for versions **17.0, 18.0, and 19.0**. The purpose of this memo is to pin down what governance-relevant primitives already exist in the Odoo ecosystem so that the `mcp_pro_governance` module can depend on them, wrap them, replace stale ones, or — where justified — fill real gaps.

All source citations refer to files on `github.com/odoo/odoo` and `github.com/OCA/*`. Where a line number is cited, it is for the `18.0` branch at the time of writing (April 2026) unless otherwise stated.

---

## 1. Native Odoo — Identity & Access

### 1.1 `res.users`, portal vs internal, shared users

Odoo partitions user accounts into three top-level classes enforced through a single field (`share` on `res.users`, derived from `groups_id`):

| User type | Defining group(s) | Billing impact | Use case |
|-----------|-------------------|----------------|----------|
| Internal | `base.group_user` | Counts against Enterprise user licences | Employees using the back-office |
| Portal | `base.group_portal` | Free | Customers / suppliers logging in to the portal |
| Public | `base.public_user` | Free | Anonymous web visitors |

The `share` boolean on `res.users` is computed: `share = True` iff the user has **no** internal group. Many security predicates (`_is_internal()`, `ir.rule` conditions, access to the `/web` client) key off `share` or `group_user`. The `/web` backend rejects portal users; portal users land on `/my`.

Key methods on `res.users` relevant to governance:

- `_is_internal(self)` — returns True if the user has `base.group_user`. Used by `res.users.apikeys.description.check_access_make_key` to forbid portal users from minting API keys at all ([res_users.py L2550](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/res_users.py#L2550)).
- `_is_admin(self)` — holds `base.group_erp_manager`.
- `_is_system(self)` — holds `base.group_system`.
- `authenticate(db, credential, user_agent_env)` — the canonical login entry point, called by `odoo.http.Request.authenticate`.
- `_check_credentials(credential, user_agent_env)` — the extension point where auth backends chain via `super()`.

### 1.2 `res.groups`, `ir.model.access`, `ir.rule`

Three layers, composed:

- **`res.groups`** — set-membership primitive. A user's `groups_id` transitively expands through `implied_ids`. Modules declare groups in XML (`<record model="res.groups">`). Categories (`ir.module.category`) group them.
- **`ir.model.access`** — coarse, table-level CRUD ACLs. Each row ties a `model_id` to a `group_id` (or global if null) and four booleans `perm_read/write/create/unlink`. Usually shipped as `security/ir.model.access.csv`. No field-level, no value-level.
- **`ir.rule`** — value-level record rules. Python-like domains evaluated against the user's context (`user.id`, `user.company_id`, groups). Distinction between `global` rules (always applied) and `groups`-scoped rules (OR-combined per group intersection — a known footgun: adding a group with permissive rules *weakens* security).

What this gives `mcp_pro_governance`: a first-class way to gate any governance configuration model behind groups and rules. What it does **not** give us: any runtime awareness of *which AI agent* is acting, per-tool or per-field scoping, budgetary limits, or temporal constraints.

### 1.3 `res.users.apikeys` — the actual model

Defined in [`odoo/addons/base/models/res_users.py`](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/res_users.py) around lines 2282–2580 in 18.0. This section gets its own deep dive in §7 below; the short tour:

- `res.users.apikeys` is `_auto = False` (manual SQL table creation in `init()`) and `_allow_sudo_commands = False`.
- Stored columns: `id`, `name`, `user_id`, `scope`, `create_date`, `expiration_date`, `index` (first 8 hex chars of the key), `key` (`pbkdf2_sha512` hash).
- Key generation uses `os.urandom(20)` hex-encoded (40 char string), stored as `pbkdf2_sha512` with 6000 rounds ("dictionary attacks on API keys isn't much of a concern", per the source comment).
- The `scope` field exists but the framework only recognises one value in core: the synthetic scope `'rpc'`. `NULL` scope = global key. There is **no enum, no catalogue of scopes, no tool-level scoping.**

### 1.4 Authentication backends

All ship in core `odoo/addons/*`:

| Addon | Purpose | Notes |
|-------|---------|-------|
| `auth_signup` | Self-service signup & password reset | Always available. |
| `auth_totp` | TOTP second factor | Since Odoo 14; forces `_rpc_api_keys_only()` to True for TOTP-enabled users, meaning password auth over RPC is refused once TOTP is on. |
| `auth_totp_mail` | Backup-code email delivery | Companion to `auth_totp`. |
| `auth_totp_portal` | TOTP for portal users | 18+. |
| `auth_oauth` | OAuth2 login (Google, Facebook, etc.) | The Odoo-native OAuth flow — it is **OAuth 1-era user-linked login**, not resource-scoped tokens. |
| `auth_ldap` | LDAP/Active Directory bind | Pre-`users_ldap` module, now folded into core. |
| `auth_passkey` | WebAuthn / FIDO2 passkeys | **New in Odoo 18.** First-class passkey registration. |

**Version deltas that matter:**

- **17 → 18:** `expiration_date` field added to `res.users.apikeys`. The `res.groups.api_key_duration` field is introduced, giving admins per-group maximum API key lifetimes. `auth_passkey` lands. `_auth_method_bearer` in `ir.http` is added as a first-class route-auth type, letting endpoints require a Bearer API key natively instead of via session cookies ([`ir_http.py L204`](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/ir_http.py#L204)).
- **18 → 19:** the apikeys schema is unchanged (verified against `master`). No JWT, no OAuth 2.1 resource-scoped tokens, no per-tool scopes, no rotation API in core. Odoo 19's security story for data+AI is essentially "use API keys with expiry" — the same as 18.

There is **no JWT issuer, no OAuth 2.0 resource-scoped token, no PAT-to-agent binding, and no rate limiting** in native Odoo in any of 17/18/19. `_auth_method_bearer` takes an Odoo-native API key, not a JWT.

---

## 2. Native Odoo — Audit

### 2.1 `mail.thread` and `mail.activity`

`mail.thread` is the mixin almost every business document inherits. It provides:

- `message_ids` — threaded `mail.message` records.
- Automatic tracking of fields declared with `tracking=True`, producing `mail.tracking.value` rows (`old_value_*` / `new_value_*`) tied to a `mail.message` of subtype `mail.mt_note` or `mail.mt_comment`.
- Followers (`mail.followers`) and subscriptions.

`mail.activity` is a **separate** model for to-do / reminder activities (call, meeting, to-do). It is not an audit mechanism — activities are freely mutable and deletable by the assignee.

### 2.2 `mail.message` subtypes

`mail.message.subtype` is an extensibility point: modules declare subtypes like `sale.mt_order_confirmed` or `project.mt_task_new`. Subtypes are how follower notifications are filtered. From a governance standpoint subtypes are a *notification routing primitive*, not an audit primitive.

### 2.3 Is there an append-only audit in core?

Short answer: **no.** `mail.message` is mutable via `unlink()` by users with delete rights on the parent record, and while admins can't delete their own messages through the UI, nothing at the storage layer prevents `DELETE FROM mail_message` from an `env.sudo()` call or a module override. The tracking values on a `mail.message` survive only as long as the message does.

The `ir.logging` table exists for framework / exception logging and is append-only at the schema level, but it is not used for business-action auditing and is typically garbage-collected.

### 2.4 What Enterprise adds

- **Studio** — lets admins add fields/tracking/reports via UI. Studio-added fields respect the same `tracking=True` rules as code-added ones, but Studio itself is not an audit system.
- **Approvals** — a workflow app for approval requests. Produces its own `approval.request` records with states; useful for human-in-the-loop gating but not an audit trail of arbitrary actions.
- **Sign** — e-signature, produces `sign.request` records. Signed documents are audit-grade only inasmuch as the PDF itself is hashed and stored.
- **IAP** (In-App Purchases) — Odoo's own billing credit system for paid API calls (SMS, SnailMail, partner enrichment). Not governance; it is billing.

Enterprise adds **no native append-only audit log** and no action-level policy engine. The advertising implies "enterprise-grade audit" via Studio + tracking, but this is marketing, not engineering.

---

## 3. OCA — Relevant Modules

Observed April 2026. All paths are `github.com/OCA/<repo>/<branch>/<module>`. "Last commit" is the date of the most recent commit touching that module's folder on the `18.0` branch (from `gh api commits`).

### 3.1 Matrix: module × Odoo version

| Module | Repo | License | 17.0 | 18.0 | 19.0 | Last commit (18.0) | Fit |
|--------|------|---------|:----:|:----:|:----:|--------------------|-----|
| `auditlog` | `OCA/server-tools` | AGPL-3 | Yes | Yes | Yes | 2026-04-01 | **High** — our default audit backend |
| `base_user_role` | `OCA/server-backend` | LGPL-3 | Yes | Yes | *check* | 2026-04-23 | Medium — useful for role templating |
| `auth_api_key` | `OCA/server-auth` | LGPL-3 | Yes | Yes | Yes | 2026-04-21 | **High** — complementary key model |
| `auth_api_key_group` | `OCA/server-auth` | LGPL-3 | Yes | Yes | Yes | 2025-04-13 | Medium — grouping extension |
| `auth_api_key_server_env` | `OCA/server-auth` | LGPL-3 | Yes | Yes | *no* | — | Low — env-driven key storage |
| `auth_jwt` | `OCA/server-auth` | LGPL-3 | Yes | Yes | *no* | 2026-02-20 | **High** — JWT bearer verification |
| `auth_oidc` | `OCA/server-auth` | AGPL-3 | Yes | Yes | Yes | 2025-11-03 | **High** — Zitadel / Keycloak / Entra login |
| `auth_saml` | `OCA/server-auth` | AGPL-3 | Yes | Yes | *no* | 2025-09-26 | Medium — enterprise SAML IdPs |
| `auth_oauth_multi_token` | `OCA/server-auth` | AGPL-3 | Yes | Yes | Yes | — | Medium — concurrent OAuth sessions |
| `auth_session_timeout` | `OCA/server-auth` | AGPL-3 | Yes | Yes | Yes | 2025-03-03 | Low — idle session kill |
| `password_security` | `OCA/server-auth` | LGPL-3 | Yes | Yes | *no* | 2025-06-14 | Medium — password policy |
| `impersonate_login` | `OCA/server-auth` | AGPL-3 | *(17 yes)* | Yes | *no* | 2026-02-18 | Medium — support-mode impersonation with its own log |
| `session_db` | `OCA/server-tools` | LGPL-3 | Yes | Yes | Yes | 2025-02-07 | **High** — Postgres-backed sessions, survives blue/green |
| `base_technical_user` | `OCA/server-tools` | AGPL-3 | Yes | Yes | Yes | 2025-03-28 | Medium — `res.company.technical_user_id` pattern |
| `vault` / `vault_share` | `OCA/server-auth` | AGPL-3 | Yes | Yes | *no* | — | Low (unrelated — end-user password vault) |

"*no*" = not currently present in that branch as of April 2026.

### 3.2 Deep dives on the modules we actually care about

**`auditlog` (OCA/server-tools)** — `AGPL-3`, v `18.0.2.0.9`. Entity model:

- `auditlog.rule` — configuration: per-model rules choosing `log_type` (`full` vs `fast`) and which CRUD verbs to record.
- `auditlog.log` — one row per logged operation. Fields: `name`, `model_id`, `model_name`, `res_id`, `res_ids`, `user_id`, `method`, `line_ids`, `http_session_id`, `http_request_id`, `log_type` ([log.py](https://github.com/OCA/server-tools/blob/18.0/auditlog/models/log.py)).
- `auditlog.log.line` — per-field before/after values.
- `auditlog.http.request` — Path, user, session context per HTTP hit ([http_request.py](https://github.com/OCA/server-tools/blob/18.0/auditlog/models/http_request.py)).
- `auditlog.http.session` — Groups HTTP requests by session.

Gaps: not append-only (rows are writable by anyone with write access on `auditlog.log`), not cryptographically chained, expensive at scale (`full` mode issues per-field subqueries). But it is the de facto audit backend in the OCA ecosystem and it integrates correctly with `ir.http` to capture HTTP request context. We should depend on it and post *supplementary* structured events there (per tool call, per agent, per budget decision).

**`auth_api_key` (OCA/server-auth)** — `LGPL-3`, v `18.0.1.0.2`. Model `auth.api.key` with `name`, `key` (plaintext!), `user_id`, `active`. Includes `_retrieve_uid_from_api_key(key)` cached via `@tools.ormcache("key")`. The key column is stored **plaintext** (the module docstring acknowledges "Enter a dummy value in this field if it is obtained from the server environment configuration"), which is different from core where keys are hashed. This module is primarily intended for machine-to-machine endpoints on top of OCA's REST controllers (e.g. `base_rest`) ([auth_api_key.py](https://github.com/OCA/server-auth/blob/18.0/auth_api_key/models/auth_api_key.py)).

Implication: there are **two parallel API-key models in the wild**: core `res.users.apikeys` (hashed, user-bound, used by `/_odoo` Bearer auth) and OCA `auth.api.key` (plaintext, one-to-one with a user, used by OCA's `base_rest`). `mcp_pro_governance` should not invent a third; it should bind policy to `res.users.apikeys.id` and optionally to `auth.api.key.id`.

**`auth_jwt` (OCA/server-auth)** — `LGPL-3`, v `18.0.1.0.2`, maintainer `sbidoul` (ACSONE). Model `auth.jwt.validator` with these crucial fields: `signature_type` (`secret` / `public_key`), `secret_key`, `public_key_jwk_uri`, `audience`, `issuer`, `user_id_strategy` (how to map the JWT subject to `res.users`), `partner_id_strategy`, plus the route-auth chain. Adds an `auth='jwt_<validator_name>'` route auth method. Depends on `pyjwt` and `cryptography`. **This is the right substrate for verifying Zitadel / Auth0 / Keycloak-issued tokens inside Odoo.**

**`auth_oidc` (OCA/server-auth)** — `AGPL-3`, v `18.0.1.1.0`. Extends core `auth_oauth` with a `flow` field accepting `access_token`, `id_token_code` (OIDC authorization code), and `id_token` (implicit, deprecated). Depends on `python-jose`. Validates the ID token signature against the provider JWKS. Used widely with Keycloak / Azure AD / Google / Zitadel for interactive browser SSO ([auth_oauth_provider.py](https://github.com/OCA/server-auth/blob/18.0/auth_oidc/models/auth_oauth_provider.py)).

**`session_db` (OCA/server-tools)** — `LGPL-3`, v `18.0.1.0.1`, co-authored by Odoo SA and ACSONE. Moves Werkzeug sessions from `filestore` to Postgres, which is mandatory for any blue/green deploy (and for multi-worker horizontal scaling). Co-authorship by Odoo SA signals Odoo's own recommended pattern.

**`base_user_role` (OCA/server-backend)** — `LGPL-3`, v `18.0.1.0.7`, maintainers `sebalix`, `jcdrubay`, `novawish`. Very active (2026-04-23). Adds a `res.users.role` model: roles are first-class and assigned to users with optional start/end dates. Group membership is *derived* from role assignments. Solves the "I want approver rights only during Q1" problem.

**`impersonate_login` (OCA/server-auth)** — `AGPL-3`, v `18.0.1.1.0`, Akretion. Adds an admin-only "log in as" action on `res.users` plus an `impersonate.log` model recording each impersonation with `impersonator_id`, `impersonated_id`, start/stop times. This is a rare example of purpose-built governance tooling in OCA — it exists precisely because support engineers need an audit trail of staff-as-user actions.

**`password_security` (OCA/server-auth)** — `LGPL-3`, v `18.0.1.0.0`. Adds minimum length / complexity rules, password expiration on `res.users`, and `res.users.pass.history`. Depends on `auth_totp`. Useful but out of scope for the MCP-governance story (we don't own the user's interactive password).

**Two-factor:** `auth_totp` is core; OCA doesn't meaningfully extend it. `auth_admin_passkey` exists in 17/18 but is *admin-only backdoor*, not MFA.

---

## 4. Odoo Enterprise — Deltas Relevant to Governance

Sourced from [Odoo 18 documentation](https://www.odoo.com/documentation/18.0/) and the Enterprise repo (private, so citations are to docs).

| App / feature | What it does | Governance-adjacent? | Honest take |
|---------------|--------------|----------------------|-------------|
| Studio | GUI field/view/automation builder | Produces auditable tracked fields, exports as a module | Useful for adding `tracking=True` quickly; not itself a policy engine |
| Approvals | Approval-request workflow | Yes — human-in-the-loop gating | Generic; not bound to AI / tool-call actions |
| Sign | E-signature | Only if you're signing a contract | Tangential |
| Documents + Workflow | DMS with rules | Weak audit trail on docs | Not for ERP actions |
| IAP | Pay-per-call vendor credits | Metering adjacent | Billing, not governance — but the *credit+consumption* UX is a useful template for MCP tool budgets |
| Mobile + Tours | — | No | — |
| Knowledge | Wiki | No | — |
| Helpdesk / Planning / etc. | Apps | No | — |

**What Enterprise does *not* add that one might hope it would:**

- No append-only audit log.
- No per-agent / per-integration identity.
- No API-key scoping beyond core (same `res.users.apikeys` as Community).
- No JWT issuer or validator.
- No rate limiting.
- No budget / quota primitive applicable to ERP actions.
- No DLP / PII-aware export controls.

Enterprise is a *product tier*, not a governance tier. `mcp_pro_governance` does not need to depend on any Enterprise module, and deliberately should not — it must install on Community.

---

## 5. Odoo + SSO in the Wild

### 5.1 Observed patterns

- **Zitadel / Keycloak / Entra ID / Auth0 for interactive login:** `auth_oidc` is the canonical answer. Configure an `auth.oauth.provider` with `flow=id_token_code`, set JWKS URL, map the `sub` claim to the user's OAuth UID, and `email` to login.
- **Machine-to-machine:** two patterns coexist:
  1. **`res.users.apikeys` per technical user** (Odoo-native Bearer auth on `/_odoo` endpoints and JSON-RPC). Pros: hashed storage, expiration, survives server restarts without redeploy. Cons: global scope, no fine-grained permissions beyond the user's groups.
  2. **`auth_jwt` with an external issuer** (Zitadel M2M grant, Auth0 client credentials, Entra service principal). Pros: no secret stored in Odoo, audience-scoped, short-lived, revocable at the IdP. Cons: requires JWKS fetch on every validator init, needs a well-configured `user_id_strategy`.

- **SAML:** `auth_saml` is maintained but lags a version behind OIDC in activity (last touched 2025-09-26). Adopt it only if a customer has a hard SAML-only IdP.

### 5.2 How `odoo-mcp-pro` (sibling) uses Zitadel today

From [`odoo-mcp-pro/mcp_server_odoo/oauth.py`](file:///Users/rutgerhofste/Documents/GitHub/odoo-mcp-pro/mcp_server_odoo/oauth.py):

> "Claude.ai acts as a public client (PKCE, no client_secret) -- this is correct per OAuth 2.1 for browser/CLI clients that cannot keep secrets. The MCP server acts as a Resource Server and validates tokens via introspection using its own client_id:client_secret (confidential). Audience validation ensures tokens are intended for this resource server."

Specifically, `ZitadelTokenVerifier` calls Zitadel's RFC 7662 introspection endpoint with `Basic client_id:client_secret`, checks `active=true`, validates audience, and extracts `sub` / `client_id` / `scopes` / `exp`. The Odoo credentials themselves are *not* in the token — they are kept in a server-side mapping from Zitadel `sub` to an Odoo API key.

### 5.3 How `odoo-mcp-pro-admin` (sibling) uses Zitadel

From [`odoo-mcp-pro-admin/mcp_server_odoo_admin/auth.py`](file:///Users/rutgerhofste/Documents/GitHub/odoo-mcp-pro-admin/mcp_server_odoo_admin/auth.py): admin web UI uses Zitadel OIDC **authorization code + PKCE**, stores PKCE verifier server-side in Postgres (survives blue/green deploys), signs an 8-hour session cookie with `itsdangerous`, and adds a role-based guard (`super_admin` / `team_admin` / `member`).

Key fact: the PKCE verifier is stored via `db_manager.store_pending_auth(state, code_verifier, redirect_uri, next_url)` in Postgres — "survives deploys" is explicitly called out in a comment. This is the same pattern we need inside Odoo if we want OIDC login to survive rolling restarts; `session_db` + careful state storage does it.

Deployment scripts in [`odoo-mcp-pro-admin/deploy/setup-zitadel.sh`](file:///Users/rutgerhofste/Documents/GitHub/odoo-mcp-pro-admin/deploy/setup-zitadel.sh) show the Zitadel objects required: one OIDC web app (for the admin UI) plus one introspection app (for the resource server) per tenant. `mcp_pro_governance` should provide *zero* infrastructure for Zitadel itself — that's the admin layer's job — but it should define an `auth.jwt.validator` out of the box that the admin layer can point at the customer's IdP.

### 5.4 What works today / what doesn't

**Works today:**
- Interactive browser SSO into Odoo via `auth_oidc` with any standards-compliant IdP.
- `res.users.apikeys` with `expiration_date` and a per-group `api_key_duration` cap, giving admins a blunt-but-real lifecycle control (since 18.0).
- `_auth_method_bearer` for first-class Bearer-auth endpoints (since 18.0).

**Doesn't work today:**
- No resource-scoped access tokens for Odoo's own API. `res.users.apikeys.scope` is a dead field in core.
- No JWT validation out of core — requires `auth_jwt`.
- No per-agent identity. An "AI agent" is indistinguishable from a user once it has a key.
- No rate limit on API key use.
- No rotation workflow (create new, mark old deprecated, revoke after window).
- No signing of outbound events for webhook receivers to verify.
- `session_db` is not enabled by default — fresh Odoo installs lose sessions on redeploy.

---

## 6. Relevant Internals — Where a Companion Module Hooks In

### 6.1 `ir.http` authentication hooks

Found at [`odoo/addons/base/models/ir_http.py`](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/ir_http.py). The extension pattern is:

```python
class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_<name>(cls):
        # custom auth logic; raise werkzeug.exceptions.Unauthorized on failure
        ...
```

Routes then opt in with `@http.route('/foo', auth='<name>')`. Core ships `_auth_method_user`, `_auth_method_public`, `_auth_method_none`, and (since 18) `_auth_method_bearer`. `auth_jwt` adds `_auth_method_jwt_<validator_name>` dynamically. This is our primary extension point for any new route.

The pre-dispatch chain, from the same file ([L261-280](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/ir_http.py#L261)):

```python
@classmethod
def _authenticate(cls, endpoint):
    auth = 'none' if http.is_cors_preflight(request, endpoint) else endpoint.routing['auth']
    cls._authenticate_explicit(auth)

@classmethod
def _authenticate_explicit(cls, auth):
    try:
        if request.session.uid is not None:
            if not security.check_session(request.session, request.env, request):
                request.session.logout(keep_db=True)
                request.env = api.Environment(request.env.cr, None, request.session.context)
        getattr(cls, f'_auth_method_{auth}')()
    except (AccessDenied, http.SessionExpiredException, werkzeug.exceptions.HTTPException):
        raise
    except Exception:
        _logger.info("Exception during request Authentication.", exc_info=True)
        raise AccessDenied()
```

Note the `session.logout(keep_db=True)` on session-token mismatch — this is the hook that invalidates sessions after password/2FA changes.

### 6.2 `odoo.service.security.check` and `check_session`

From [`odoo/service/security.py`](https://github.com/odoo/odoo/blob/18.0/odoo/service/security.py):

```python
def check(db, uid, passwd):
    res_users = Registry(db)['res.users']
    return res_users.check(db, uid, passwd)

def compute_session_token(session, env):
    self = env['res.users'].browse(session.uid)
    return self._compute_session_token(session.sid)

def check_session(session, env, request=None):
    self = env['res.users'].browse(session.uid)
    expected = self._compute_session_token(session.sid)
    if expected and odoo.tools.misc.consteq(expected, session.session_token):
        if request:
            env['res.device.log']._update_device(request)
        return True
    return False
```

`check()` verifies a user/password pair (and honours `auth_totp` via `_check_credentials`). `check_session()` verifies a session token derived from the user's hashed password, the user's session salt, and the session id — which is why changing a password invalidates all sessions. Since 18, it also updates `res.device.log`, giving us a simple "where has this user logged in from" table to join against.

### 6.3 How credentials propagate

- `request.session.uid` is the authenticated user id for the current HTTP request.
- `request.env` is an `odoo.api.Environment` bound to that uid; `env.user` is the browse record.
- `request.update_env(user=uid)` replaces the environment's user (this is what `_auth_method_bearer` does on successful API-key validation).
- Model code generally does not have access to `request` outside HTTP handlers — `odoo.http.request` is a `werkzeug.local.Local` proxy. For long-running crons or RPC calls there is no request; audit hooks must not assume one exists.

Extension seam for governance: an override of `ir.http._authenticate_explicit` or a new `_auth_method_mcp` that (a) verifies the token, (b) reads a `mcp.agent` record, (c) enforces the agent's policy (rate, scope, allowed tools, budget), then (d) calls `super()._auth_method_<user|bearer>`. This lets us slot in without forking any core behaviour.

---

## 7. `res.users.apikeys` — The Deep Dive

### 7.1 Schema (as of 18.0)

From [`res_users.py` L2349-2410](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/res_users.py#L2349):

```python
class APIKeys(models.Model):
    _name = 'res.users.apikeys'
    _description = 'Users API Keys'
    _auto = False                 # manual SQL table creation
    _allow_sudo_commands = False  # prevent sudo bypass tricks

    name = fields.Char("Description", required=True, readonly=True)
    user_id = fields.Many2one('res.users', index=True, required=True, readonly=True, ondelete="cascade")
    scope = fields.Char("Scope", readonly=True)
    create_date = fields.Datetime("Creation Date", readonly=True)
    expiration_date = fields.Datetime("Expiration Date", readonly=True)

    def init(self):
        # CREATE TABLE ... id, name, user_id FK, scope, expiration_date,
        #   index varchar(8) NOT NULL CHECK (char_length(index) = 8),
        #   key varchar NOT NULL,
        #   create_date ... DEFAULT (now() at time zone 'utc')
        # CREATE INDEX ON (user_id, index)
```

Constants in the same file (L2282-2288):

```python
API_KEY_SIZE = 20        # bytes
INDEX_SIZE = 8           # hex digits (= 4 bytes, 20% of the 40-char key)
KEY_CRYPT_CONTEXT = CryptContext(
    ['pbkdf2_sha512'], pbkdf2_sha512__rounds=6000,
)
```

The comment in-source acknowledges the low round count: *"default is 29000 rounds which is 25~50ms, which is probably unnecessary given in this case all the keys are completely random data: dictionary attacks on API keys isn't much of a concern"*. The comment is *reasonable*: 160 bits of entropy is outside brute-force range regardless of round count, and 6000 rounds keeps `_check_credentials` fast.

### 7.2 Storage — what is hashed, what is plaintext

- The **key column stores only the pbkdf2\_sha512 hash.** Plaintext is returned to the UI exactly once, in `_generate()`, and displayed in the `res.users.apikeys.show` transient model. Never stored plaintext in the DB.
- The **index column stores the first 8 hex chars of the plaintext key** (20% of the key). This is used to narrow the PBKDF2 verification to a single row during `_check_credentials` — otherwise every request would re-hash against every key in the database.

### 7.3 Creation flow

1. **UI:** Settings → Users → [user] → Security tab → `New API Key` button, which invokes `res.users.apikey_wizard()` opening the `res.users.apikeys.description` transient.
2. The transient collects `name`, `duration` (days: 1, 7, 30, 90, 180, 365, optional `0`=persistent and `-1`=custom — but `0` and the upper durations are available only to system users, otherwise bounded by `res.groups.api_key_duration`).
3. `make_key()` is decorated with `@check_identity` — it **forces the user to re-enter their password** via `res.users.identity_check` before minting a key. This is why portal users can't mint keys even with the transient open; `check_access_make_key` blocks them at `_is_internal()`.
4. `_generate(scope, name, expiration_date)`:

```python
k = binascii.hexlify(os.urandom(API_KEY_SIZE)).decode()
self.env.cr.execute("""
INSERT INTO {table} (name, user_id, scope, expiration_date, key, index)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id
""".format(table=self._table),
[name, self.env.user.id, scope, expiration_date or None,
 KEY_CRYPT_CONTEXT.hash(k), k[:INDEX_SIZE]])
```

The raw key is returned **once** and displayed via `res.users.apikeys.show`. Never again retrievable.

5. **There is no public HTTP endpoint named `/_odoo/security/activate_api_key`** in 18.0 core. The creation flow is backend-only (requires an authenticated session, passes the identity check, returns the key via an Odoo action). External tooling that programmatically mints a key must do so over authenticated JSON-RPC to `res.users.apikeys.description`.

### 7.4 Verification flow

`_check_credentials(scope, key)` ([L2403](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/res_users.py#L2403)):

```python
assert scope and key, "scope and key required"
index = key[:INDEX_SIZE]
self.env.cr.execute('''
    SELECT user_id, key
    FROM {} INNER JOIN res_users u ON (u.id = user_id)
    WHERE u.active and index = %s
      AND (scope IS NULL OR scope = %s)
      AND (expiration_date IS NULL OR expiration_date >= now() at time zone 'utc')
'''.format(self._table), [index, scope])
for user_id, current_key in self.env.cr.fetchall():
    if key and KEY_CRYPT_CONTEXT.verify(key, current_key):
        return user_id
```

Note: `(scope IS NULL OR scope = %s)` — a key with `scope=NULL` matches *any* requested scope. There is no scope hierarchy, no deny-list, no tool-level enforcement. Today, core uses only `scope='rpc'`, so effectively every key is global.

### 7.5 Rate limiting

**None.** There is no counter in `res.users.apikeys` and no middleware throttling API-key-authenticated requests in core. An infinite-loop script with a valid key will hammer `/jsonrpc` until the worker dies.

### 7.6 Revocation

- **Manual:** `remove()` on a key → soft-checked ownership (`env.is_system() or user_id == env.user`), then `sudo().unlink()`.
- **Automatic expiration:** `_gc_user_apikeys()` is decorated `@api.autovacuum` ([L2463](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/res_users.py#L2463)):

```python
DELETE FROM res_users_apikeys
 WHERE expiration_date IS NOT NULL AND expiration_date < now() at time zone 'utc'
```

Expired keys are deleted entirely (not soft-deleted). This means the audit trail of *which key was used for what* is lost when the key is garbage-collected — a problem we must solve in `mcp_pro_governance`.

- **Cascading:** archive a user and `active = false` blocks `_check_credentials` at SQL level. Delete a user and `ON DELETE CASCADE` wipes their keys.

### 7.7 Gap analysis for AI-agent use

| Requirement | Core has it? | Notes |
|-------------|:-----------:|-------|
| Hashed at rest | Yes | `pbkdf2_sha512` |
| Expiration | Yes (18+) | Admin-settable max per group |
| Per-tool scopes | **No** | `scope` field exists but unused |
| Per-model / per-method scopes | **No** | — |
| Agent identity distinct from user | **No** | Always bound to `res.users` |
| Rate limit | **No** | — |
| Cost / budget | **No** | — |
| Rotation workflow | **No** | Can issue new + revoke old, but no workflow support |
| Usage audit | Partial | `_logger.info` on issue/remove only; no per-use log |
| Scope assertion at check time | Partial | Only `rpc` used; `_auth_method_bearer` hardcodes `scope='rpc'` |
| Binding to IdP subject | **No** | No `oauth_sub` / `jwt_sub` column |
| Per-key IP allowlist | **No** | — |
| Machine / non-user principal | **No** | Must create a real `res.users` row; technical-user pattern from OCA is the closest thing |

This is exactly the gap `mcp_pro_governance` exists to fill — not by replacing `res.users.apikeys` (it is sound for what it does), but by adding a sibling `mcp.agent` record, a `mcp.agent.key` binding to `res.users.apikeys`, a `mcp.tool.scope` catalogue, per-call audit, and budget/rate-limit enforcement in an `_auth_method_mcp`.

---

## 8. Packaging & App-Store Constraints

### 8.1 `__manifest__.py` required fields

From [Odoo 18 module manifest docs](https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html#reference-backend-module-manifest):

- `name` (string, required) — human-readable.
- `version` (string, required). Convention: `<odoo_version>.<x>.<y>.<z>` — e.g. `18.0.1.0.0`. The Apps Store parses the leading version to gate installability.
- `license` (string) — one of `GPL-2`, `GPL-2 or any later version`, `GPL-3`, `GPL-3 or any later version`, `AGPL-3`, `LGPL-3`, `Other OSI approved licence`, `OPL-1`, `Other proprietary`. If absent, defaults to `LGPL-3`.
- `depends` (list of strings) — Odoo module dependencies. Manifest validation requires `base` transitively.
- `category` (string) — app category; for governance modules `Technical` or `Administration` are common.
- `summary` (string) — shown on the app tile.
- `description` (string or falsy) — if absent, the Apps Store renders `static/description/index.html`.
- `data` (list of file paths relative to the module root) — XML/CSV loaded on install.
- `demo` (list) — loaded only when demo mode is enabled.
- `installable`, `application`, `auto_install` (booleans).
- `external_dependencies` (dict `python: [...]`, `bin: [...]`) — required but not auto-installed.
- `price`, `currency` — only if selling on the Enterprise App Store.
- `images` (list of relative paths) — cover image in `static/description/`.
- `assets` (dict) — bundle assignment (`web.assets_backend`, `web.assets_frontend`).

### 8.2 License constraints on the Apps Store

Sources: [Odoo Apps FAQ](https://apps.odoo.com/apps/faq), [Odoo Licensing](https://www.odoo.com/documentation/18.0/legal/licenses.html).

- Odoo Community Edition 18/19 is **LGPL-3**.
- Modules published as **paid** on the Enterprise Apps Store must use **OPL-1** (Odoo Proprietary License v1).
- Modules published as **free** on the Community Apps Store can use any OSI-approved licence: LGPL-3, AGPL-3, GPL-3, etc.
- **LGPL-3 is compatible with AGPL-3** — an AGPL-3 module can depend on LGPL-3 core without violating either licence, but any module that depends on an AGPL-3 module inherits AGPL-3 copyleft for the combined work.
- OCA convention: `server-auth` is mixed LGPL-3 / AGPL-3, `server-tools` is mixed. LGPL-3 is preferred for modules that are likely to be depended on widely; AGPL-3 is used for "application" style modules where the copyleft is intended.

**Recommendation for `mcp_pro_governance`:** **LGPL-3**. It maximises adoption — enterprise users with proprietary extensions can depend on it without opening their code, and it matches the licence of `auth_api_key`, `auth_jwt`, and `session_db` (the modules we will depend on most heavily). AGPL-3 would be preferable only if we want to force downstream disclosure of SaaS wrappers — but we already have a separate SaaS layer (`odoo-mcp-pro-admin`) and hobbling it with AGPL obligations is self-inflicted.

### 8.3 Versioning conventions

`<odoo_major>.<odoo_minor>.<feature>.<minor>.<patch>` — e.g. `18.0.1.0.0` for the first release targeting Odoo 18. The first two segments must match the target Odoo major; apps that branch per Odoo version publish one line per branch.

### 8.4 Icon, description, screenshots

- `static/description/icon.png` — square, typically 140x140, PNG with transparent background.
- `static/description/index.html` — HTML landing page rendered on the app page. Odoo strips scripts; inline styles allowed.
- `static/description/banner.png` or similar — hero image (optional).
- Screenshot carousel lives in files referenced from `index.html`.

### 8.5 Review process and timelines

- Submission: [apps.odoo.com/apps/upload](https://apps.odoo.com/apps/upload).
- Review SLA: Odoo documentation gives no hard timeline; community reports on the Odoo forum range **2 days to 3 weeks** for free apps, longer for paid due to the paid-app checks (screenshots, legal name match, payout settings).
- Review is manual by Odoo staff; common rejection causes: missing `LICENSE`, `license` manifest field mismatch, Enterprise-only dependencies in a Community-tier submission, modifying Odoo core in non-upgrade-safe ways.

### 8.6 Practical testing constraints

- Module must install cleanly into a fresh Odoo Community DB of the declared version without warnings.
- Tests should live under `tests/` using `odoo.tests.common.TransactionCase` / `HttpCase`.
- Runboat (Runbot for OCA) provides free CI for OCA modules; third-party modules need their own CI (GitHub Actions with the `OCA/odoo-addons-tester` action or similar).
- Odoo 18 requires Python 3.10+; Odoo 19 requires Python 3.11+.

---

## 9. Synthesis

### What already exists and we should depend on / integrate with

- **`res.users.apikeys` (core)** — keep as the on-the-wire credential for Bearer auth. Our agent records bind *to* these keys, we do not replace them.
- **`ir.http._auth_method_*`** — extension seam for a new `_auth_method_mcp`.
- **`mail.thread` + tracking** — use on governance config records for change tracking (policy edits, agent creation, etc.).
- **`OCA/server-tools/auditlog` (AGPL-3)** — optional dependency; when present, we emit supplementary `auditlog.log` rows for governance events so customers see them in the familiar UI. Not a hard dependency (AGPL-3 would taint us).
- **`OCA/server-tools/session_db` (LGPL-3)** — recommend as a deployment prerequisite; we can verify presence in `__manifest__` post-install or in a config check.
- **`OCA/server-auth/auth_jwt` (LGPL-3)** — hard-ish dependency for IdP-issued token verification. If the customer uses Zitadel / Auth0 / Entra, `auth_jwt` is the path. We provide a default `auth.jwt.validator` config template.
- **`OCA/server-auth/auth_oidc` (AGPL-3)** — document as the recommended way to get SSO browser login; *not* a code dependency because of AGPL-3.
- **`OCA/server-auth/auth_api_key` (LGPL-3)** — soft dependency: when present, allow `mcp.agent` to bind to an `auth.api.key` in addition to `res.users.apikeys`, so existing OCA REST users aren't forced to migrate.
- **`OCA/server-backend/base_user_role` (LGPL-3)** — soft dependency: allow agent policies to reference roles, not just groups.

### What exists but is too thin / stale / incompatible and we must replace or wrap

- **`res.users.apikeys.scope`** — the field is there but unused; the *concept* of a scope catalogue must be owned by our module (`mcp.tool.scope` with verbs, models, prefixes). We wrap, not replace.
- **`res.users.apikeys` GC** — deletes expired keys, losing audit lineage. We must copy key metadata (id, name, user_id, create_date, expiration_date, hash of the index) into a `mcp.agent.key.archive` model on revocation / before GC.
- **`auth_api_key` plaintext storage** — acceptable for the OCA REST use case but not for ours. If we allow binding to `auth.api.key`, we warn in the UI that the key is stored plaintext and prefer `res.users.apikeys`.
- **`auditlog` mutability** — `auditlog.log` rows are writable. We write our events through `auditlog` for UX, but *also* into our own `mcp.audit.event` model with `create_date` DEFAULT + `ir.rule` deny-all-write + optional hash chaining.
- **Core "audit" story** — `mail.thread` tracking is not evidentiary. We supply a dedicated append-only event stream.
- **No rate limit anywhere** — we must implement it ourselves, either in-process (token-bucket in Python with `cache.memoize`) or via a configurable backend (Redis).

### What is genuinely missing in the ecosystem — the gap we are justified in filling

1. **Agent identity as a first-class model.** Nothing in core, Enterprise, or OCA has a "this caller is an AI agent operated by person X on behalf of tenant Y" record. `base_technical_user` adds a `res.company.technical_user_id` field but it's cosmetic.
2. **Per-tool / per-method scopes on Odoo credentials.** `res.users.apikeys.scope` is a placeholder; nobody uses it beyond `'rpc'`.
3. **Append-only action audit tied to (agent × tool × input-hash × output-hash).** `auditlog` records model CRUD, not tool calls. `mail.message` is mutable.
4. **Budget / quota / rate-limit primitives for business actions.** IAP does this for Odoo's own paid API calls but is not reusable for tenant-defined limits on tenant-defined tools.
5. **Policy engine for agent actions** — "this agent may read `sale.order` but only write `crm.lead` and only during business hours and only under 100 calls/hour and only if the total invoice draft it creates is under €10 000." Nothing comparable exists.
6. **Outbound event signing** — no module signs webhook payloads for downstream receivers.
7. **A governance-focused dashboard.** Even with `auditlog` + `impersonate_login` + `auth_session_timeout` all installed, there is no single pane of glass.

### Open questions for synthesis

1. **Dependency posture:** do we make `auth_jwt` a hard dependency (clean, but excludes customers who can't install OCA modules) or bundle a minimal JWT verifier and *recommend* `auth_jwt`? Preliminary answer: hard dependency on `auth_jwt`, soft on the rest.
2. **Licence choice:** confirm **LGPL-3** — matches `auth_jwt`, maximises downstream reuse. Revisit only if we later decide SaaS forks must open-source.
3. **Enterprise compatibility:** we must install on Community. Should we also ship optional Enterprise integrations (e.g. an Approvals-based human-gate when an agent exceeds a budget)? If yes, those live in a *separate* `mcp_pro_governance_approvals` bridge module.
4. **Odoo 17 support:** the 17.0 `res.users.apikeys` has **no `expiration_date`** — a material gap for us. Either (a) refuse to install on 17 and declare 18+, (b) ship a 17-only migration that adds the column via our own SQL. Preliminary answer: 18.0+ only. 17.0 LTS customers can use `auth_jwt`-only mode without the API-key lifecycle.
5. **`auditlog` coupling:** store a *pointer* from `mcp.audit.event` to `auditlog.log.id` when the latter is installed, or duplicate the data? Preliminary: pointer + summary snapshot, because `auditlog` rows can be archived by customers.
6. **Agent-to-user binding:** every agent call still needs an Odoo user for `ir.rule` evaluation. Do we (a) require one "shadow" `res.users` per agent (cheap, but hits Enterprise user licence counting for internal groups), (b) allow multiple agents to share a single technical user (fewer licences, loses per-agent row-level security), or (c) route agent calls through a synthetic "impersonation" so rules evaluate against the *operator*? Preliminary: (a) for internal agents, (c) for agents acting on behalf of an end user.
7. **How does `_check_credentials` reliably know which agent fired a request** when all it sees is a Bearer token? We need a new column on `res.users.apikeys` (impossible — `_auto=False`, we can't ALTER it safely without a core patch) *or* a side-table `mcp.agent.key` keyed on `res.users.apikeys.id`. Preliminary: side-table.
8. **Rate-limit backend:** pure in-process (per-worker, inconsistent across workers) vs. Postgres advisory locks + counter table (consistent, slower) vs. optional Redis (fastest, extra dependency). Preliminary: Postgres default, optional Redis via adapter.
9. **Session persistence during policy updates:** if we change an agent's scope mid-session, how is it invalidated? `session_token` is recomputed on password/2FA change, not on group change. We may need to bump a `mcp.agent.policy_version` into the session and re-check on every `_auth_method_mcp` call.

---

*End of memo. Primary sources linked inline; see §7 for the line-accurate extract of the core API-key implementation, and §3 for the OCA matrix with last-commit timestamps as of 2026-04.*
