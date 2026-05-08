# 04 — MCP Ecosystem, Fine-Grained Authorization and Agent Audit

*Research memo for `odoo-mcp-pro-governance`. Focus: how the Model Context
Protocol ecosystem and adjacent authorization / audit stacks handle
identity, scopes, authorization and audit for AI agents, and what of that
is reusable inside Odoo.*

Primary sources: the MCP specification (revision **2025-06-18**), IETF RFCs
8707 / 7591 / 9700 / 9396 / 9728 / 9068, OAuth 2.1 draft-13, OpenTelemetry
GenAI semantic conventions, Cerbos / OpenFGA / Permit.io / Zitadel vendor
docs, and the code of Pantalytics' own MCP server at
`/Users/rutgerhofste/Documents/GitHub/odoo-mcp-pro` (`oauth.py`,
`access_control.py`, `tools.py`).

---

## MCP specification — authorization

The authoritative document is the MCP Authorization specification, revision
**2025-06-18** ([modelcontextprotocol.io/specification/2025-06-18/basic/authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)).
It defines an HTTP-transport-only profile. For stdio transport, the spec
explicitly says "Implementations using an STDIO transport **SHOULD NOT**
follow this specification, and instead retrieve credentials from the
environment" — that matches how MCP Pro already behaves in Claude Desktop
(see `oauth.py` docstring).

### Framework: OAuth 2.1 + RFC 9728 + RFC 8414

MCP bolts together four established specifications and uses a deliberately
narrow subset:

- OAuth 2.1 ([draft-ietf-oauth-v2-1-13](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13))
- OAuth 2.0 Authorization Server Metadata ([RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414))
- Dynamic Client Registration ([RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591))
- Protected Resource Metadata ([RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728))

The normative core:

> "Authorization servers **MUST** implement OAuth 2.1 with appropriate
> security measures for both confidential and public clients."

> "MCP servers **MUST** implement OAuth 2.0 Protected Resource Metadata
> ([RFC9728](https://datatracker.ietf.org/doc/html/rfc9728)). MCP clients
> **MUST** use OAuth 2.0 Protected Resource Metadata for authorization
> server discovery."

> "MCP servers **MUST** use the HTTP header `WWW-Authenticate` when
> returning a *401 Unauthorized* to indicate the location of the resource
> server metadata URL."

The MCP server is always an OAuth 2.1 *resource server*. The authorization
server is explicitly out of scope — "The implementation details of the
authorization server are beyond the scope of this specification. It may be
hosted with the resource server or a separate entity."

### Resource Indicators (RFC 8707) — mandatory

RFC 8707 lets a client tell the authorization server which resource server
the token is for, so the AS can audience-restrict the token
([RFC 8707 §2](https://www.rfc-editor.org/rfc/rfc8707.html#section-2)).
MCP makes this binding mandatory on both sides:

> "MCP clients **MUST** implement Resource Indicators for OAuth 2.0 as
> defined in [RFC 8707](https://www.rfc-editor.org/rfc/rfc8707.html) to
> explicitly specify the target resource for which the token is being
> requested."

> "MCP clients **MUST** send this parameter regardless of whether
> authorization servers support it."

> "MCP servers **MUST** validate that access tokens were issued
> specifically for them as the intended audience, according to RFC 8707
> Section 2."

The canonical URI rules matter for governance design: "valid canonical
URIs" are of the form `https://mcp.example.com/mcp`, without fragment and
preferably without trailing slash. Path components are allowed where they
identify a specific MCP server instance — `https://mcp.example.com/server/mcp`.
This is the hook for tying tokens to a specific Odoo tenant/database, not
just to "an MCP server somewhere".

### Dynamic Client Registration (RFC 7591)

DCR is **SHOULD**, not MUST — but the spec strongly incentivises it:

> "MCP clients and authorization servers **SHOULD** support the OAuth 2.0
> Dynamic Client Registration Protocol ([RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591))
> to allow MCP clients to obtain OAuth client IDs without user interaction."

The rationale given is important for Odoo: "Clients may not know all
possible MCP servers and their authorization servers in advance. Manual
registration would create friction for users." For a single-tenant Odoo
module, DCR may feel excessive; for a hosted MCP Pro, it is effectively
the only scalable option. A follow-up spec revision
([November 2025](https://aaronparecki.com/2025/11/25/1/mcp-authorization-spec-update))
adds enterprise-managed client registration as a middle ground.

### PKCE — mandatory

> "To mitigate this, MCP clients **MUST** implement PKCE according to
> OAuth 2.1 Section 7.5.2."

The spec treats PKCE as the baseline, not an extra: public clients
(Claude Desktop, Claude.ai, Cursor, Windsurf) cannot keep a client secret,
so PKCE carries the burden of authorization-code-binding.

### Token usage, audience, scopes

Token placement is explicit:

> "MCP client **MUST** use the Authorization request header field ... `Authorization: Bearer <access-token>` ... Access tokens **MUST NOT** be
> included in the URI query string."

> "Authorization **MUST** be included in every HTTP request from client
> to server, even if they are part of the same logical session."

The spec is agnostic about whether tokens are JWT or opaque, but it points
at [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068.html) (JWT Profile
for OAuth 2.0 Access Tokens) for the `aud` claim. Introspection
([RFC 7662](https://datatracker.ietf.org/doc/html/rfc7662)) is allowed —
this is exactly what MCP Pro's `ZitadelTokenVerifier` uses today
(`/Users/rutgerhofste/Documents/GitHub/odoo-mcp-pro/mcp_server_odoo/oauth.py` L99-L169).

Scope semantics are **not standardised by MCP**. The spec's "Scope
Minimization" section says only:

> "Minimal initial scope set (e.g., `mcp:tools-basic`) containing only
> low-risk discovery/read operations ... Incremental elevation via
> targeted `WWW-Authenticate` `scope="..."` challenges when privileged
> operations are first attempted."

> "Down-scoping tolerance: server should accept reduced scope tokens;
> auth server **MAY** issue a subset of requested scopes."

Concrete implication for Odoo: the module has to define its own scope
catalogue; MCP only says "keep it small and progressive".

### Sampling — server calls the client's LLM

Sampling (`sampling/createMessage`) inverts the direction: the server asks
the client to run an LLM call on its behalf. The security implications
are severe because the server can indirectly steer prompts toward user
data the client already has access to. The spec places all the human
gates on the *client*:

> "For trust & safety and security, there **SHOULD** always be a human in
> the loop with the ability to deny sampling requests."

> "Clients **SHOULD** implement user approval controls ... Both parties
> **MUST** handle sensitive data appropriately."

A governance module inside Odoo has no way to enforce this — it lives on
the server side and cannot see the client's approval UI. What it *can*
enforce is: whether this server is allowed to call `sampling/createMessage`
at all, and what it is allowed to put in the prompt. A policy axis
worth exposing.

### Additional MUSTs worth internalising

From the [Security Best Practices document](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices):

> "MCP servers **MUST NOT** accept any tokens that were not explicitly
> issued for the MCP server." (Token Passthrough)

> "The MCP server **MUST NOT** pass through the token it received from
> the MCP client" to upstream APIs.

> "MCP servers that implement authorization **MUST** verify all inbound
> requests. MCP Servers **MUST NOT** use sessions for authentication."

The last one rules out a common Odoo instinct — reusing an Odoo session
cookie to "remember" an agent. Each MCP request must re-verify its token
from scratch.

---

## MCP specification — tools, resources, prompts

### Tool annotations

Tool definitions carry an optional `annotations` object describing tool
behaviour. The spec's
[Tools page](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
defines fields used across the ecosystem (`readOnlyHint`, `destructiveHint`,
`idempotentHint`, `openWorldHint`, `title`). The SDKs (`mcp.types.ToolAnnotations`,
already imported in `tools.py` L16) expose them directly to server code.

Crucial qualifier:

> "For trust & safety and security, clients **MUST** consider tool
> annotations to be untrusted unless they come from trusted servers."

This is a governance trap. A server can *claim* a tool is `readOnly` and
clients are told not to believe it. For Odoo that means annotations cannot
be the only signal — the module has to enforce read-only at the XML-RPC /
JSON-RPC layer against the Odoo model, not trust the declared annotation.
MCP Pro already does this correctly in `access_control.py` (L135-L157):
it uses Odoo's `check_access_rights` per CRUD operation.

For governance, the annotations are still useful as *declared* intent, so
a policy can say "tool claims destructive → require manager approval, and
double-check via model-level write ACL".

### Consent UX

The spec puts consent on the client side, with strong shoulds:

> "Applications **SHOULD**: Provide UI that makes clear which tools are
> being exposed to the AI model; Insert clear visual indicators when
> tools are invoked; Present confirmation prompts to the user for
> operations, to ensure a human is in the loop."

And on the server side:

> "Servers **MUST**: Validate all tool inputs; Implement proper access
> controls; Rate limit tool invocations; Sanitize tool outputs."

Rate limiting is listed as a MUST. MCP Pro has a `UsageTracker`
(`tools.py` L109-L111) calling `check_rate_limit(sub)`. The governance
module has to cover that.

### Resource templates

Resource templates (`uriTemplate` via [RFC 6570](https://datatracker.ietf.org/doc/html/rfc6570))
are the spec's mechanism for parameterised resources — e.g.
`odoo://res.partner/{id}`. This maps extremely well to Odoo: a template
per model, with the ID completed via `completion/complete`. The spec's
only normative access-control text on resources is:

> "Servers **MUST** validate all resource URIs. Access controls **SHOULD**
> be implemented for sensitive resources. Resource permissions **SHOULD**
> be checked before operations."

So resources are effectively "audit like tools, authorise like tools".

### Logged tool-call trace schema

MCP does not specify an audit format. There is no "tool call log event".
Servers log tool usage into their own sinks. The only protocol-level
envelope is the JSON-RPC request/response pair:

```json
{ "jsonrpc": "2.0", "id": 2, "method": "tools/call",
  "params": { "name": "get_weather", "arguments": { "location": "NYC" } } }
```

with reply containing `content`, `structuredContent`, and `isError`.
Everything else — who called it, which session, which token, which user —
is host-implementation-specific. Clients "**SHOULD**: Log tool usage for
audit purposes" but the schema is free-form.

OpenTelemetry GenAI (see section 7) fills this gap with
`execute_tool {gen_ai.tool.name}` spans. That is the de-facto industry
standard even though the MCP spec doesn't require it.

---

## Reference implementations and how they actually handle authz/audit

### `@modelcontextprotocol/sdk` — TypeScript

The TS SDK ships `McpServer`, `StreamableHttpServerTransport`, and
`OAuthProvider` helpers. The official `simple-auth` example expects the
implementer to provide a `TokenVerifier`. Audience validation is *not*
enforced by default — the SDK hands the access token to the verifier and
the verifier decides. PKCE, DCR and RFC 8707 are supported at the client
side (`@modelcontextprotocol/sdk/client`) but the server side is still
largely hand-rolled for multi-tenancy. Ecosystem reports say "The SDK
provides foundational OAuth 2.1 validation but delegates most advanced
security patterns to custom implementation".

### `mcp` Python SDK

Shipped as `mcp` on PyPI, with `mcp.server.auth.provider.TokenVerifier`
as the pluggable validation surface — this is exactly what MCP Pro
extends (`oauth.py` L32, `class ZitadelTokenVerifier(TokenVerifier)`).
`mcp.server.auth.middleware.auth_context.get_access_token()` gives
per-request access to the current token inside a tool handler (used in
`tools.py` L101-L107).

The Python SDK currently does not:

- enforce audience validation; the docstring merely says "Access token
  is assumed to be valid" — MCP Pro re-implements this check manually
  (`oauth.py` L123-L133).
- emit OTel spans for tool calls — no built-in audit.
- verify that the client sent `resource=...` in the token request; this
  is the *authorization server's* job per RFC 8707, not the RS.

This is the "gap" MCP Pro has already filled by hand and what a
governance module should formalise.

### Three community MCP servers — how they scope access

| Server | Auth | Scope model | Audit | Source |
|---|---|---|---|---|
| **GitHub MCP server** (`github/github-mcp-server`) | OAuth device flow to GitHub; token used as GitHub token | Inherits GitHub OAuth scopes (`repo`, `read:org`, ...); no MCP-layer scope | GitHub audit log — not MCP | [GitHub](https://github.com/github/github-mcp-server) |
| **Cloudflare remote MCP** | OAuth 2.1 + RFC 9728 + DCR; Cloudflare Workers | Custom scopes per tool surface | Workers logs | [Cloudflare blog](https://blog.cloudflare.com/model-context-protocol/) |
| **Supabase MCP** (`supabase-community/supabase-mcp`) | PAT (bearer) or OAuth in hosted mode | Project-scoped tokens, no per-tool scope | Supabase audit trail | [GitHub](https://github.com/supabase-community/supabase-mcp) |
| **Pantalytics MCP Pro** | OAuth 2.1 via Zitadel introspection; stdio falls back to env | No per-scope model; Odoo ACLs + rate limit + audience | No durable audit — stdout logs | `oauth.py`, `access_control.py`, `tools.py` |

The pattern is clear: **nobody has a rich scope model yet**. Most servers
either (a) inherit upstream scopes, (b) expose one omnibus scope, or (c)
use bearer tokens with no MCP-layer scope at all. Odoo-level authz gets
done by leaning on the backend's native ACL system (what MCP Pro does
with `check_access_rights`).

Gaps across reference code:

1. **Audit is ad-hoc.** Most use language-native logging; few emit
   structured, queryable events.
2. **Audience validation is commonly skipped.** Only a minority of servers
   in the 2025-11 [state-of-MCP-auth writeup](https://stackoverflow.blog/2026/01/21/is-that-allowed-authentication-and-authorization-in-model-context-protocol/)
   were found to correctly reject tokens with wrong `aud`.
3. **No per-tool policy engine.** Tool exposure is binary
   (enabled/disabled at startup) in almost all servers.
4. **Human-in-the-loop for destructive ops is inconsistent** despite the
   `destructiveHint` annotation existing.

---

## Fine-grained authorization projects that plug into MCP / agent stacks

| Project | Model | Core primitives | PDP delivery | MCP integration | Hosted? |
|---|---|---|---|---|---|
| **Cerbos** | ABAC + roles, YAML policies | principal, resource, action, conditions | Self-hosted sidecar (gRPC/HTTP) or Cerbos Hub managed | [Cerbos + FastMCP blog post](https://www.cerbos.dev/blog/mcp-authorization) — explicit pattern for enabling tools per session | Cerbos Hub (managed) |
| **OpenFGA / Auth0 FGA** | ReBAC, Zanzibar-inspired | type definitions, tuples, relations, check / list-objects / list-users | Self-hosted PDP; Auth0 FGA = hosted | [`evansims/openfga-mcp`](https://github.com/evansims/openfga-mcp) exposes FGA as an MCP server; [`aaguiarz/openfga-modeling-mcp`](https://github.com/aaguiarz/openfga-modeling-mcp) for authoring | Auth0 FGA |
| **Permit.io** | Hybrid RBAC/ABAC/ReBAC via OPA + OpenFGA | principal, resource, action, tenant, attributes; "MCPermit" / "Permit MCP Gateway" | Local PDP container (sidecar), managed control plane | [docs.permit.io/ai-security/mcp-permissions](https://docs.permit.io/ai-security/mcp-permissions/) — 5-stage auth, HITL approvals, ReBAC, prompt filtering (PII / jailbreak guardrails via partner models) | Yes |
| **Oso Cloud** | Polar policy language | actor, action, resource, facts | Hosted; local PDP with data facts | No MCP-native integration published as of 2026-04; generic REST | Yes |
| **SpiceDB (AuthZed)** | ReBAC, Zanzibar-spec-compliant | schema, relationships, checks | Self-hosted; AuthZed Cloud | No first-party MCP server; community bindings only | AuthZed |

### Cerbos

Core concepts (per [Cerbos docs](https://docs.cerbos.dev/cerbos/latest/)):
policies bind **actions** (strings like `read`, `approve_expense`) to
**resources** (typed objects with attributes) based on the **principal**
(user id + roles + attributes) and arbitrary **conditions** written in
CEL. The PDP is a stateless service; the PEP lives inside the application
and sends `checkResource` requests. Because it is stateless, fact-free,
and YAML-driven, it is the easiest to deploy next to Odoo — an Odoo
module can bundle a Cerbos sidecar and ship policies as module data.

Cerbos for MCP specifically (per their [MCP blog post](https://www.cerbos.dev/blog/mcp-authorization)):

1. MCP client connects; MCP server extracts the identity.
2. On `tools/list`, server asks Cerbos "which of these tools is this
   principal allowed to call?" Tools that come back `allow` are exposed;
   the rest are hidden from `tools/list`.
3. On `tools/call`, server asks Cerbos again with the tool arguments as
   resource attributes for ABAC conditions.

Useful because the spec says annotations are untrusted — Cerbos lets the
*server* enforce the same intent the annotation declares, with an
audited policy trail.

### OpenFGA / Auth0 FGA

ReBAC model: store `user:X relation object:Y` tuples, define
`authorization_model` with types and relations, query with `check`. Good
fit for Odoo's object graph (a partner is_member_of a company;
a sale.order belongs_to a partner; a user is_salesperson_of a team).
`check(user:alice, can_approve, sale.order:42)` is the natural mental
model. Two Odoo-specific complications:

- Odoo ACLs are already expressed as record rules and `ir.model.access`;
  duplicating them as tuples is synchronisation work.
- OpenFGA tuples are external data; Odoo already has the graph. A lighter
  path is to use OpenFGA only for cross-cutting questions Odoo can't
  easily answer (e.g. "is this AI agent allowed to act on behalf of this
  human on this model?").

### Permit.io

Permit's [MCP permissions architecture](https://docs.permit.io/ai-security/mcp-permissions/)
(as summarised in Permit's [blog](https://www.permit.io/blog/authorization-strategies-for-model-context-protocol-mcp))
wraps three layers: OAuth 2.1 identity, ReBAC policy evaluation, and a
"Permit MCP Gateway" that sits between client and server. Distinctive
features vs Cerbos / OpenFGA:

- **HITL approvals**: a `request_access` / `approve` workflow for
  sensitive tool calls, with the approval state stored in the PDP.
- **Prompt filtering** (claimed): PII scrubbing and jailbreak-detection
  in front of the tool call, usually via partner models.
- **Access requests in natural language**: an LLM-backed path for users
  to ask for scope elevation.

Permit's gateway essentially turns authorization into a proxy
responsibility, which is a different architecture than embedding a PDP
in the MCP server. For Odoo we probably want embedded (lower latency,
easier audit correlation with the Odoo row) rather than a proxy.

### Oso / SpiceDB

- **Oso Cloud** uses Polar (their own DSL); nice for expressiveness but
  the DSL is the lock-in. No published MCP-native pattern.
- **SpiceDB** is the purest Zanzibar implementation; attractive if we
  already had a Zanzibar-shaped identity graph, otherwise heavy.

---

## OAuth 2.1, resource indicators, scope design

### RFC 8707 — exact semantics

From [RFC 8707 §2](https://www.rfc-editor.org/rfc/rfc8707.html#section-2):

- The `resource` parameter is "an absolute URI"; **MUST NOT** include a
  fragment; **SHOULD NOT** include a query component.
- The authorization server "**SHOULD** audience-restrict issued access
  tokens to the resource(s) indicated by the `resource` parameter".
- The AS signals audience via the JWT `aud` claim or RFC 7662
  introspection responses.
- Multiple `resource` parameters MAY appear but "using only a single
  `resource` parameter is encouraged".
- Error code `invalid_target` for bad / unknown resources.

Design consequence for `mcp_pro_governance`: the module should let an
admin define the canonical URI string that their MCP Pro instance expects
(per database), and reject tokens whose `aud` does not contain it.
MCP Pro already takes an `expected_audience` constructor argument
(`oauth.py` L54).

### Scope best practice (RFC 6749 §3.3 + RFC 9700)

From [RFC 9700](https://datatracker.ietf.org/doc/html/rfc9700) and the
MCP "Scope Minimization" section:

- "The privileges associated with an access token **SHOULD** be
  restricted to the minimum required for the particular application or
  use case." (RFC 9700)
- "Access tokens **SHOULD** be audience-restricted to a specific
  resource server or, if that is not feasible, to a small set of resource
  servers."
- Do *not* emit a huge scope catalogue in `scopes_supported`; don't use
  wildcard scopes (`*`, `all`, `full-access`); don't bundle unrelated
  privileges to preempt future prompts.
- Prefer progressive elevation via `WWW-Authenticate: Bearer scope="..."`
  challenges on first privileged call.

### How to design scopes for Odoo

There are three viable axes; pick one or combine:

**A. CRUD-on-model scopes (`odoo:read:res.partner`, `odoo:write:sale.order`).**
Precise, enumerable, maps 1:1 to Odoo's `ir.model.access`. Downside:
explodes in number (N models × 4 operations); triggers the "scope
inflation" anti-pattern the MCP spec warns about. Probably too granular
to put in tokens directly.

**B. Functional scopes (`finance:read`, `finance:write`, `crm:manage`,
`inventory:view`).** Maps to Odoo *modules* (accounting, CRM, stock).
Maintainable, user-comprehensible on the consent screen, aligns with how
Odoo already groups permissions. Downside: still needs translation to
per-model ACLs inside the server.

**C. Scope = coarse capability + RFC 9396 Rich Authorization Requests
for precision.** Use something like `mcp:tools` / `mcp:tools:destructive`
as the scope and let `authorization_details` carry the model list and
CRUD mask:

```json
{
  "type": "odoo_model_access",
  "locations": ["https://mcp.example.com/db/prod"],
  "actions": ["read", "write"],
  "datatypes": ["res.partner", "sale.order"]
}
```

[RFC 9396 §2](https://datatracker.ietf.org/doc/html/rfc9396) defines
`locations`, `actions`, `datatypes`, `identifier`, `privileges` as
standard fields — they fit this use case almost word-for-word. The
downside is that RAR support across MCP clients is thin in 2026; Zitadel
supports it but Claude Desktop / Claude.ai do not emit
`authorization_details` yet.

**Recommendation for Odoo.** Start with **B (functional scopes)** for
user-visible consent, combined with `check_access_rights`-based
enforcement inside the module (what MCP Pro already does). Reserve **C**
(RFC 9396) as an optional advanced mode for organisations with their own
AS.

---

## Zitadel as an MCP / agent identity provider

[Zitadel](https://zitadel.com) is the AS that MCP Pro already uses. It is
relevant for the governance module because it already provides most of
what we would otherwise have to re-invent.

### Features relevant to agents

From Zitadel docs ([Projects](https://zitadel.com/docs/guides/manage/console/projects),
[User Service v2](https://zitadel.com/docs/apis/resources/user_service_v2)):

- **Projects** are the permission container; applications and roles hang
  off them. "Assert roles on authentication" and "include roles in
  access/ID tokens" are project-level toggles.
- **Roles**: key (code-level identifier), display name, group. All
  applications in a project share roles — this is convenient: one role
  like `mcp.agent.finance` can be reused by multiple MCP clients.
- **Service accounts** (a.k.a. machine users, formerly "service users"):
  non-interactive principals; authenticate via **private-key JWT**,
  **client credentials**, or **Personal Access Tokens (PAT)**. "PATs are
  currently only available for machine users/service accounts and are
  ready-to-use tokens that can be sent directly in the authentication
  header."
- **Actions v2**: pre- and post-flow hooks that let you mutate token
  content server-side — useful for injecting Odoo-specific claims
  (database, company_id) into the access token without changing client
  code.
- **Impersonation / delegation**: Zitadel supports token exchange
  (RFC 8693) — an MCP server can request a downstream token on behalf of
  a user, which is exactly the pattern needed when MCP Pro calls the
  Odoo JSON-RPC layer *as* the user.

### API keys vs OIDC tokens for MCP

| Dimension | OIDC access token (human) | Zitadel PAT (service account) | Private-key JWT (service account) |
|---|---|---|---|
| Lifetime | Short (minutes to 1h) | Long-lived, user-set expiry | Short (signed JWT, seconds) |
| Rotation | Refresh token | Manual revocation | Rotate the signing key |
| Audience | Can be RFC 8707 restricted | Opaque; aud set by Zitadel | Aud in JWT |
| Interactive consent | Yes (PKCE) | No (pre-issued) | No |
| Fit for MCP | Claude Desktop, Claude.ai, any browser-capable client | n8n, cron jobs, fixed integrations | Backend-to-backend, ephemeral agents |
| MCP spec alignment | Full (OAuth 2.1) | Works as a bearer token; no DCR / PKCE path | Same |

Practical consequence: MCP Pro's governance module should accept
*both* — OIDC for human-driven agents, PAT/JWT for background agents —
and record the authentication method on the audit row so the SoD logic
can react ("night-time PAT just ran a refund" is different from
"interactive OIDC user ran a refund").

### How MCP Pro already uses Zitadel

From the sibling repo:

- `oauth.py:32` — `ZitadelTokenVerifier` uses RFC 7662 introspection
  with `client_id:client_secret` Basic auth.
- `oauth.py:123-133` — enforces audience: token `aud` must contain
  `expected_audience` (configured per deployment).
- `oauth.py:138-142` — checks `required_scopes` (currently optional).
- `oauth.py:145` — extracts `sub` from the introspection response and
  treats it as the identity carried through the request.
- `tools.py:101-107` — pulls the verified token from the MCP auth
  context, uses `access_token.client_id` (= Zitadel `sub`) as the
  tenant / user key for connection lookup.
- `access_control.py` — enforces CRUD rights via Odoo's native
  `check_access_rights`, cached for 5 minutes per model.

What is *not* in MCP Pro today:

- Structured audit events (only Python logging).
- Per-tool policy decisions — access is purely at the Odoo-model ACL
  layer.
- Human-in-the-loop approval workflow for destructive tools.
- Scope-to-capability mapping; scopes are currently a bag of strings
  without a schema.

These are the gaps the governance module fills.

---

## Audit patterns for AI agents (outside MCP too)

### OpenTelemetry GenAI semantic conventions

From [OTel GenAI spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/):

Span naming:

- Inference: `{gen_ai.operation.name} {gen_ai.request.model}` (e.g.
  `chat claude-opus-4`)
- Retrieval: `{gen_ai.operation.name} {gen_ai.data_source.id}`
- **Tool execution**: `execute_tool {gen_ai.tool.name}` — this is the
  one the governance module cares about most.

Standard attributes on a tool-call span:

- `gen_ai.operation.name` (`execute_tool`, `chat`, `invoke_agent`)
- `gen_ai.provider.name` (`anthropic`, `openai`, `aws.bedrock`,
  `gcp.vertex_ai`)
- `gen_ai.tool.name`
- `gen_ai.tool.type` (`function`, `extension`, `datastore`)
- `gen_ai.tool.call.id` — opaque identifier shared between LLM log and
  tool execution log; this is the bridge between an LLM trace and an
  Odoo audit row.
- `gen_ai.tool.call.arguments` (opt-in, large, potentially sensitive)
- `gen_ai.tool.call.result` (opt-in)
- `gen_ai.request.model` / `gen_ai.response.model`
- `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`
- `error.type` on failure

There is also a dedicated "Model Context Protocol" conventions page under
GenAI — OTel explicitly recognises MCP as a first-class source of spans.

### LangSmith / Langfuse / Helicone

[Langfuse data model](https://langfuse.com/docs/observability/data-model):

- **Traces** ≈ one user interaction (the analogue of an Odoo transaction).
- **Observations** ≈ individual LLM calls, retrievals, or tool calls
  nested under a trace. Types include `generation`, `span`, `event`.
- **Sessions** group traces (multi-turn chat).
- Arbitrary `user_id`, `session_id`, `tags`, `metadata` propagate from
  trace to all observations — useful because it means a single Odoo
  `request_id` placed on the trace shows up on every child call.

LangSmith and Helicone use the same trace/span/generation shape with
different names. All three capture input/output by default, which is a
compliance hazard for Odoo data — the governance module should let an
operator pick whether to export I/O or only metadata.

What is applicable inside Odoo: the **trace / observation hierarchy**
maps cleanly onto a parent "AI session" record and child "tool call"
records. The `request_id` is the backbone — reuse it as
`gen_ai.tool.call.id` so an external Langfuse / OTel backend can
correlate with Odoo rows.

### Enterprise audit log schemas — common fields

| Field | Microsoft Purview (Copilot audit) | AWS CloudTrail (Bedrock Agents) | GCP Cloud Audit (Vertex AI) |
|---|---|---|---|
| Who | `UserId`, `UserKey` | `userIdentity.arn`, `userIdentity.type` | `authenticationInfo.principalEmail` |
| What | `Operation` (e.g. `CopilotInteraction`) | `eventName` (`InvokeAgent`, `InvokeModel`) | `methodName` (`aiplatform.googleapis.com/...`) |
| When | `CreationTime` (ISO 8601 UTC) | `eventTime` | `timestamp` |
| Where (resource) | `ObjectId`, sensitivity label | `resources[].ARN` | `resource.name`, `resource.type` |
| Request ID | `Id` (GUID) | `requestID`, `eventID` | `insertId`, `operation.id` |
| App identity | `AppId`, `AgentId` (Agent 365) | `userAgent`, agent ID in resources | `serviceName`, `methodName` |
| Payload refs | File refs w/ sensitivity label, prompts via DSPM | Not by default; requires data-trail | Request/response stored separately (data access logs) |
| Outcome | `ResultStatus` | `errorCode`, `errorMessage` | `status.code`, `status.message` |

Common-denominator schema — *this is what the governance module should
emit*:

- `id` (ULID/UUID, serves as `request_id`)
- `timestamp` (UTC ISO 8601)
- `principal.sub` (Zitadel `sub`)
- `principal.type` (`human`, `service_account`)
- `principal.auth_method` (`oidc`, `pat`, `jwt_profile`)
- `client.name` / `client.id` (DCR client id)
- `tool.name`
- `tool.annotations.*` (declared)
- `resource.uri` (Odoo model + id)
- `action` (`read` / `write` / `create` / `unlink` / `execute`)
- `outcome` (`allow` / `deny` / `error`) + `outcome_reason`
- `policy.engine` / `policy.id` (which PDP decided)
- `sampling.used` (bool — did the server call `sampling/createMessage`?)
- `token.aud`, `token.scope`
- `correlation.trace_id` (W3C trace-context) / `correlation.tool_call_id`
- Optional: `payload.input_hash`, `payload.output_hash` (never the
  payload itself unless explicitly opted in and sensitivity-labelled)

---

## Concrete patterns worth stealing

Short, specific, implementable:

1. **One `request_id` flows through the whole chain.** Generate a ULID at
   the MCP server on first request-per-session and stamp it as:
   `gen_ai.tool.call.id` in the OTel span, a header sent back to the
   client, and the primary key of the Odoo audit row. One identifier is
   the Rosetta stone between the LLM log and the ERP log.

2. **Token audience = `https://{host}/db/{db_name}`.** Bind tokens to an
   Odoo *database*, not just to "the MCP server". Cross-database replay
   stops being a confused-deputy risk. Use the canonical URI format
   allowed by RFC 8707 (no trailing slash, no fragment).

3. **"Declared vs enforced" pairing on every tool.** Record both the
   declared annotation (`destructiveHint: true`) and the enforcement path
   that validated it (`check_access_rights unlink → True`). Mismatches
   are a governance signal.

4. **Use `WWW-Authenticate` scope challenges for elevation.** Default
   every agent to `mcp:tools-basic`; return 403 with
   `WWW-Authenticate: Bearer scope="finance:write"` when a privileged
   tool is called. This is the MCP spec's recommended pattern and works
   with vanilla OAuth clients.

5. **Per-client consent registry.** Before forwarding any auth to
   Zitadel, check a local "has this client_id already been consented for
   this tenant + scope?" table. Prevents the confused-deputy attack
   described in the MCP security best practices.

6. **Human-in-the-loop via "access request" records.** Permit.io's model
   maps cleanly onto Odoo: create an `mcp.approval.request` record when
   a destructive tool is attempted; block the tool until a human approves
   it in Odoo; then release the pending request and let the original
   request proceed. This reuses Odoo's existing approval UX (it already
   has `studio.approval.rule` in Enterprise).

7. **Audit both the attempt and the decision.** Log the `allow` path and
   the `deny` path, with the policy identifier. Denied attempts are the
   highest-signal audit rows — they are the prompt-injection and the
   jailbreak probes.

8. **Separate the PDP from the PEP.** Even if the "PDP" is just a set of
   Python functions today, keep the interface narrow
   (`decide(principal, resource, action, context) -> Decision`) so it can
   be swapped for Cerbos or OpenFGA later without touching tool code.

9. **Hash-and-store payloads, never the payload itself by default.**
   `sha256(arguments)` + `sha256(result)` gives forensic replay ability
   (did the same call happen again?) without landing PII in the audit
   trail.

10. **Sampling is a capability, not a right.** Tools that request
    `sampling/createMessage` should be whitelisted per-agent. Default
    deny.

---

## Patterns to adopt in `mcp_pro_governance`

- **Model the audit row as the common-denominator schema** from the
  enterprise comparison above. Single `mcp.audit.log` Odoo model with
  those fields; one row per tool call attempt (allowed or denied).
- **Keep Odoo ACLs as the last line of defence**, not the only line.
  `check_access_rights` stays; a policy engine sits in front of it.
- **Define scopes in two layers**: functional (`finance:read`, ...) for
  token-carried consent; per-model CRUD enforced internally via Odoo
  ACLs. Optionally accept RFC 9396 `authorization_details` for callers
  that can emit them.
- **Ship a pluggable PDP interface.** In-process Python engine as
  default; Cerbos sidecar adapter as documented extension; OpenFGA
  adapter as a pattern sample.
- **Build the approval-request workflow in Odoo itself.** Reuse the
  `studio.approval.rule` pattern if Enterprise, plain state machine if
  Community.
- **Expose OTel GenAI semantic conventions** (`execute_tool`,
  `gen_ai.tool.*`) on an optional exporter. Default off (so the module
  works air-gapped); one-flag on.
- **Treat service accounts (Zitadel PAT / JWT) as a different
  trust tier.** Separate policy class; log `principal.auth_method`; allow
  admins to disallow destructive tools for non-interactive principals.
- **Record declared vs enforced annotations.** Catches drift between
  what the tool manifest claims and what the server actually does.
- **Hash payloads by default; full payload capture is opt-in and
  sensitivity-label-aware.**
- **Never use sessions for authentication.** Per MCP security BCP —
  validate the token on every request; no Odoo session shortcut.

## Dependencies we should expect callers to bring

The governance module sits *inside Odoo*. It does not replace MCP Pro
and does not replace the AS. Clear dependency contract:

- **MCP Pro (or equivalent MCP server in front of Odoo)** handles:
  OAuth 2.1 flow, PKCE, `resource` parameter, 401/WWW-Authenticate, token
  introspection or JWT validation, audience enforcement, rate limiting,
  and transport.
- **Authorization Server (Zitadel, Keycloak, Auth0, etc.)** handles:
  user authentication, MFA, consent UI, token issuance, RFC 7591 DCR if
  supported, `aud` / `scope` claims, token revocation, and
  (if used) RFC 8693 token exchange.
- **MCP host (Claude Desktop / Claude.ai / Cursor / Windsurf)** handles:
  user-facing consent for sampling, visible tool-call review UI, PKCE on
  the client side, and local credential storage.
- **OpenTelemetry exporter / log sink (optional)** handles: durable
  storage and search of span data for cross-system correlation.
- **Optional external PDP (Cerbos / OpenFGA / Permit.io)** handles:
  central policy storage, policy versioning, GitOps, and cross-service
  reuse of the same policies.

The governance module itself owns:

- The policy authoring surface in Odoo (mcp.policy model).
- The approval-request workflow.
- The `mcp.audit.log` and its retention / export.
- Per-tool / per-model / per-scope declarations and their mapping.
- The "declared vs enforced" reconciliation check.
- Scope-catalogue management and the consent-registry table.

## Open questions for synthesis

1. **Where does the PDP live?** In-process (simplest, hardest to reuse
   across non-Odoo services) vs sidecar (Cerbos / OpenFGA — more
   operationally heavy, but re-usable). Is MCP Pro's future the Odoo
   module or a standalone deployment?
2. **Do we adopt RFC 9396 from day one, or start with functional scopes
   only?** RFC 9396 is the cleaner long-term fit for CRUD-on-model
   authorization, but client support in 2026 is still thin.
3. **How do we reconcile Zitadel roles with Odoo groups?** Today
   MCP Pro keys on Zitadel `sub` and uses Odoo's ACL; the governance
   module may need a bi-directional mapping (Zitadel role → Odoo group)
   to let admins manage in either system.
4. **Sampling policy.** Is `sampling/createMessage` blocked by default?
   What does an allowlisted sampling call *look like* in the audit row?
5. **Retention.** Purview-style long-retention vs GDPR-driven short
   retention — the audit row contains a `sub`, which is personal data.
   Default window? Per-tenant override?
6. **Integration with Odoo's own `mail.message` / `base_automation`
   logs.** Should AI-triggered changes land in `mail.message` with a
   distinctive author type so they are visible in chatter? Good for UX,
   potentially noisy.
7. **Multi-tenant MCP Pro vs single-tenant Odoo.** MCP Pro supports
   multi-tenant registries; the governance module lives inside *one*
   Odoo database. What's the contract for the tenant boundary — is
   the canonical URI always database-scoped?
8. **How much of OWASP LLM Top 10 (LLM01 Prompt Injection, LLM06
   Sensitive Info Disclosure, LLM07 Insecure Plugin Design) do we
   explicitly claim to mitigate?** That answer drives whether "prompt
   filtering" (à la Permit) belongs in scope for this module or is
   delegated to the MCP host.

---

*Sources inline. Key specs: [MCP 2025-06-18 authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization),
[MCP tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools),
[MCP security best practices](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices),
[RFC 8707](https://datatracker.ietf.org/doc/html/rfc8707),
[RFC 7591](https://datatracker.ietf.org/doc/html/rfc7591),
[RFC 9700](https://datatracker.ietf.org/doc/html/rfc9700),
[RFC 9396](https://datatracker.ietf.org/doc/html/rfc9396),
[RFC 9728](https://datatracker.ietf.org/doc/html/rfc9728),
[OTel GenAI spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/).
Internal: `oauth.py`, `access_control.py`, `tools.py` in `odoo-mcp-pro`.*
