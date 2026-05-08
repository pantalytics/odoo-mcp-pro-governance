# Synthesis — design consequences for `mcp_pro_governance`

Written after memos 01–06. This document turns findings into
commitments: what the module is, what it is not, what it ships, and in
what order. Everything here is traceable to at least two memos; where a
decision rests on only one source it is flagged.

> **Forcing function.** EU AI Act Art. 26 (deployer obligations), Art. 12
> (record-keeping), Art. 13 (transparency) and Art. 50 (transparency for
> AI-generated content) all become applicable on **2026-08-02** —
> roughly 100 days from today. A defensible v1 must be installable and
> operable by that date. Everything else in the roadmap flows from that
> deadline.
>
> **Target Odoo version: 19.0.** Python 3.11+. See §2 for the
> `auth_jwt`-on-19.0 dependency caveat and §3 for the three
> resolution paths.

---

## 1. What the module is (and is not)

**Is:** an open-source Odoo 18.0+ module (LGPL-3) that adds the five
primitives the whitepaper, the standards corpus, the Microsoft
reference architecture, and the AI-incident literature all independently
call for:

1. **Agent identity** — a first-class, non-user principal with owner,
   sponsor, lifecycle, classification, and a verifiable audit link
   (memo 01 §"Primitives Microsoft makes explicit that Odoo lacks";
   memo 02 hard requirement #2; memo 05 top-ranked v1 risk; memo 06
   white space #1).
2. **Scoped, rate-limited, expiring credentials** bound to an agent
   identity rather than to a human user (memo 03 §7.7 gap table;
   memo 04 scope design; memo 02 hard requirement #3).
3. **Append-only, hash-chained audit** with prompt hash, request id,
   principal chain, sensitivity label, trifecta flags (memo 02 hard
   requirement #1; memo 04 common-denominator schema; memo 05 top
   v1 risk #5).
4. **Policy + approval engine** for agent actions — pluggable PDP,
   HITL approvals for destructive calls, lethal-trifecta gate
   (memo 04 patterns #6–8; memo 05 top v1 risk #4; memo 01
   Copilot-Studio-DLP pattern).
5. **Transparency + incident machinery** — per-agent System Card,
   structured incident record, DPIA/AIIA template, multi-regime
   export (memo 02 hard requirements #5, 6, 8, 9; memo 01 RAI
   Transparency Notes).

**Is not:**

- A replacement for `res.users`, `res.groups`, `ir.rule`,
  `ir.model.access` or `res.users.apikeys`. We instrument around them.
- A replacement for OCA `auditlog`, `base_user_role`, `auth_saml`,
  `auth_oidc`, `auth_api_key`, `auth_jwt`. We integrate where
  licenses allow.
- A DLP product for prompts and responses leaving Odoo (that is
  Microsoft Purview / Netskope / the MCP host's concern — memo 06
  "don't build" table).
- An AI-TRiSM console (Credo, Holistic, Fiddler, IBM watsonx
  govern the model side — memo 06).
- A Copilot-Studio-style environment-based tenancy system. Odoo's
  companies and databases are our tenancy primitives.

## 2. License, target, distribution

| Decision | Choice | Rationale |
|---|---|---|
| License | **LGPL-3** | Matches `auth_jwt`, `session_db`, `auth_api_key` (memo 03 §8.2); lets Pantalytics' paid SaaS layer keep its current license; permissive enough to draw OCA contributors. AGPL-3 considered and rejected — the viral effect would be self-inflicted on our own hosted variant. |
| Odoo target | **19.0** | Current production line for Pantalytics deployments; `res.users.apikeys` schema unchanged from 18 so all 18-era primitives apply (memo 03 §1, §7). 17.0 support would require a column-adding migration that we will not carry; 18.0 support may be added later as a back-port branch if customer demand appears. |
| Python | ≥ 3.11 | Odoo 19.0 requirement (memo 03 §8.6). |
| Distribution | GitHub + apps.odoo.com + OCA-compatible layout | App-store discovery is high even if quality modules are sparse (memo 06 §9). |
| Versioning | `18.0.x.y.z` per Odoo convention | Memo 03 §8.3. |
| Sub-modules | Separate optional bridge modules for Zitadel, Enterprise Approvals, SIEM export | Keep the core dependency graph minimal. |

## 3. Dependency contract

Three tiers — hard, soft, documented-but-not-shipped.

**Hard (required at install time):**
- `base`, `mail` — Odoo core.
- `auth_jwt` (OCA/server-auth, LGPL-3) — IdP-issued token verification
  path. Without it we'd bundle a partial JWT verifier; better to rely
  on the maintained one (memo 03 §9).
  **Blocker on 19.0:** per memo 03, `auth_jwt` had not been ported to
  the 19.0 branch at the time of research. Resolution paths, in
  preference order:
  1. Contribute the 19.0 port upstream to OCA/server-auth before v0.2
     lands (most disciplined, longest lead-time).
  2. Vendor a minimal JWT verifier (~200 LoC around `python-jose` or
     `authlib`) and keep the integration seam compatible with
     `auth_jwt` so we can drop the internal copy when the OCA port
     lands.
  3. Ship `mcp_pro_governance` against 18.0 first and refactor to 19.0
     once OCA catches up.
  Current recommendation: path (1) as primary, (2) as fallback if OCA
  timing slips past our 2026-08-02 deadline.

**Soft (opt-in; integrate richer UX when present):**
- `auditlog` (OCA/server-tools, **AGPL-3**) — we emit supplementary
  `auditlog.log` rows for UX; never depend on it at code level because
  the AGPL-3 would taint `mcp_pro_governance`. Pointer-only integration
  (memo 03 §9, memo 02).
- `auth_api_key` (OCA, LGPL-3) — bind `mcp.agent.key` to an
  `auth.api.key` when customers already use it. Warn in UI: plaintext
  storage vs PBKDF2 (memo 03 §3).
- `session_db` (OCA, LGPL-3) — recommended deployment prerequisite.
- `base_user_role` (OCA, LGPL-3) — let policies reference roles, not
  just groups.

**Documented recipes (no code dependency):**
- `auth_oidc` (AGPL-3) for SSO browser login.
- `auth_saml` (OCA) for SAML customers.
- Zitadel / Keycloak / Entra ID as identity providers, via the optional
  `mcp_pro_governance_sso_zitadel` bridge module.

**What we never touch:** the `res.users.apikeys` schema. The table is
declared `_auto=False`; ALTER is not safe (memo 03 §7.7). A **side
table** `mcp.agent.key` holds our metadata and foreign-keys back.

## 4. Data model

Anchored on the Microsoft decomposition (memo 01) but collapsed to match
ERP cardinality: thousands of active agents per tenant is implausible,
so one `mcp.agent` model absorbs blueprint + identity, with an optional
`template_id` self-reference for fleets. Decision: **collapsed** model,
revisit only if a deployment actually exceeds 500 active agents.

### 4.1 Core tables (v0.2–v0.5)

| Model | Purpose | Key fields (compressed) | Memo refs |
|---|---|---|---|
| `mcp.agent` | Agent identity | name, state (draft/active/suspended/revoked), classification, provider, owner_id, sponsor_id, creator_id, user_id (shadow `res.users`), risk_score, transparency_note_id, template_id, active | 01, 02, 05, 06 |
| `mcp.agent.template` | Fleet blueprint (optional) | name, default_scope_ids, default_policy_id, inheritable_description | 01 |
| `mcp.agent.key` | Credential binding | agent_id, apikey_id (→ `res.users.apikeys`), auth_api_key_id (optional → `auth.api.key`), scope_ids, expiration_date, rate_limit_id, budget_id, rotation_due, archived_hash | 03, 04 |
| `mcp.tool.scope` | Scope catalogue | code (`finance:read`), kind (functional \| model_crud), model_ids, verbs | 04 |
| `mcp.policy` | Policy record | target (agent / scope / tool), effect (allow/deny/approval/warn), conditions (time, monetary_cap, record_volume, principal_auth_method), trifecta_rule_id | 01, 05 |
| `mcp.trifecta.rule` | Lethal-trifecta gate | session_window_s, flags_any_two (warn), flags_all_three (deny+justify) | 05 |
| `mcp.audit.event` | Append-only event | request_id (ULID, pk), create_date, agent_id, principal_chain (json), action, model_name, res_ids, tool_scope, prompt_hash, input_hash, output_hash, decision, decision_reason, sensitivity_label, trifecta_flags, merkle_prev, merkle_self | 01, 02, 04, 05 |
| `mcp.approval.request` | HITL queue | agent_id, tool_scope, proposed_action (json), requester_uid, approver_group_id, state, approval_audit_id | 04, 02 |
| `mcp.incident` | Structured incident | severity, classification (NIS2 \| DORA \| AI Act Art. 73 \| GDPR \| internal), first_detected, root_cause, audit_event_ids, nis2_report_blob, dora_report_blob, ai_act_report_blob | 02 |
| `mcp.system.card` | AI system card | agent_id, intended_purpose, limitations, evaluations, model_transparency, rai_note, version, accountable_role_id | 01, 02 |
| `mcp.dpia` | DPIA / AIIA template | system_card_id, art_26_9_xref, processing_activity_id, risk_assessments, mitigations, review_state | 02 |

### 4.2 Append-only enforcement

From memo 02 hard requirement #1 and memo 05 audit-failure patterns:
`mcp.audit.event.write()` and `unlink()` always raise `AccessError` —
no exceptions, not even for `group_mcp_governance_manager`. Retention
is enforced by a rotate-to-cold-store cron, never by delete.

Hash chain: each row stores `sha256(prev.merkle_self || row_bytes)`.
Daily root is optionally anchored externally (RFC 3161 TSA or a public
blockchain) via a future sub-module.

### 4.3 Rename from v0.1

The scaffolded `mcp.governance.agent.identity` and
`mcp.governance.audit.log` names (current repo) are **deprecated** in
favour of the shorter `mcp.agent` / `mcp.audit.event` above. Rationale:
shorter identifiers, consistent prefix, matches the `mcp_pro_*`
module-family naming. The v0.1 scaffold will be rewritten in v0.2 with
data-migration SQL (it has not shipped externally — no App Store users
exist yet).

## 5. Auth seam

A new `_auth_method_mcp` sits in front of the core `_auth_method_bearer`
(memo 03 §6). Flow:

1. `ir.http` receives request with `Authorization: Bearer <token>`.
2. Core `_auth_method_bearer` validates PBKDF2 against
   `res.users.apikeys`; if OK, sets `request.uid`.
3. Our wrapper looks up `mcp.agent.key.apikey_id == hit`, resolves
   `mcp.agent`, populates a `request.env.context['agent_id']` plus a
   server-level thread-local `mcp_ctx` (principal chain).
4. Pre-call policy evaluation: scope in allowed list, rate limit not
   exceeded, budget not exceeded, trifecta gate not tripped,
   approval-request exists if policy demands.
5. On pass: emit the **attempt** audit event with `decision=allow`,
   continue to tool execution.
6. On fail: emit the **attempt** audit event with
   `decision=deny/approve_required`, raise the appropriate response
   (`403 WWW-Authenticate: Bearer scope="finance:write"` per MCP BCP).

Tokens without an associated `mcp.agent.key` continue to work as plain
Odoo API keys — backwards compatible. We only *govern* agent
credentials, not all API activity.

## 6. Policy decision point (PDP)

From memo 04 patterns #8: keep the PDP surface **narrow and pluggable**.
Ship an in-process Python engine as default; Cerbos sidecar and OpenFGA
adapters as separately-packaged extensions. Interface:

```
Decision = decide(principal, resource, action, context)
         # Decision in {allow, deny, require_approval, warn}
         # returns (decision, reason_code, policy_id)
```

This is a contract, not an implementation. The v0.3 in-process engine
evaluates `mcp.policy` records in Odoo; Cerbos adapter translates them
to Cerbos DSL; OpenFGA adapter translates them to tuples. Policy
authoring UI lives inside Odoo either way.

**Sampling as a capability**: `sampling/createMessage` is allow-listed
per agent; default deny (memo 04 pattern #10).

## 7. Standards-to-feature cross-walk

Memo 02 hard requirements map to feature deliverables. Each audit row
and each system-card field is tagged with the clause it answers; this
drives the "Automated cross-walk badges" soft recommendation.

| Hard requirement (memo 02) | Primitive | v |
|---|---|---|
| Immutable audit log, hash chain, ≥6-month retention | `mcp.audit.event` + rotation + hash chain | 0.5 |
| Agent identity register | `mcp.agent` | 0.2 |
| Tool allow-list with least-privilege scopes | `mcp.tool.scope` + `mcp.agent.key.scope_ids` | 0.2 |
| Kill-switch, per-decision override, approval gates | `mcp.agent.state=suspended`; `mcp.approval.request`; policy effect=approval | 0.2–0.4 |
| AI system card per agent | `mcp.system.card` | 0.4 |
| Instructions-for-use artefact | System-card section (Art. 13) | 0.4 |
| Training/fine-tune data register | Out of scope — points at `mcp_pro` provider metadata | — |
| DPIA / AIIA template | `mcp.dpia` | 0.5 |
| Incident register with structured export | `mcp.incident` + generators | 0.5 |
| Vendor / ICT third-party register | Out of scope — GRC concern | — |
| Content-provenance labelling (Art. 50) | Audit row `output_hash` + `model_transparency_ref` | 0.5 |
| RoPA linkage | `mcp.dpia.processing_activity_id` | 0.5 |
| Regulatory register | `mcp.system.card` refs versioned Art. XX citations | 0.5 |
| Mandatory SoD configurations | `mcp.policy` conflict-matrix seed | 0.4 |

## 8. Roadmap, anchored to 2026-08-02

Every slice ships a demonstrable feature; no slice half-wires a
requirement.

### v0.1 — Scaffold (DONE, April 2026)

Delivered. Will be **rewritten** in v0.2 — see §4.3.

### v0.2 — Identity + scoped keys + auth seam (target mid-May 2026)

- Rename models to the §4.1 schema.
- `mcp.agent` with lifecycle + shadow `res.users`.
- `mcp.agent.key` binding + scope catalogue seed.
- `_auth_method_mcp`.
- Rate limit (Postgres counter table, Redis adapter stub).
- Soft deps: `auditlog`, `auth_api_key`.

### v0.3 — Policy + trifecta (target mid-June 2026)

- `mcp.policy` + in-process PDP.
- `mcp.trifecta.rule` + session-window detector.
- `mcp.approval.request` state machine (Community default).
- MCP BCP `WWW-Authenticate` scope challenges.

### v0.4 — System card, SoD, transparency (target mid-July 2026)

- `mcp.system.card` with Art. 13 fields and RAI Transparency Note.
- SoD conflict matrix (seed list from ISACA / memo 05 §3).
- Per-agent violation report (Copilot-Studio-DLP analogue, memo 01).
- Optional `mcp_pro_governance_approvals` sub-module (Enterprise-only
  integration with `studio.approval.rule`).

### v0.5 — Audit chain, incidents, DPIA — EU AI Act deadline 2026-08-02

- `mcp.audit.event` hash chain + daily root + retention policies per
  regime (6m AI Act / 5y DORA / 7y financial).
- `mcp.incident` with NIS2 / DORA / AI Act Art. 73 / GDPR 72h report
  generators from a single record.
- `mcp.dpia` template + Art. 26(9) cross-reference.
- Automated cross-walk export (AI RMF / ISO 42001 / AI Act / OWASP /
  MITRE ATLAS).
- **Ready for production deployer use on 2026-08-02.**

### v0.6 — Bridges & optional sub-modules (Aug–Sep 2026)

- `mcp_pro_governance_sso_zitadel` — Zitadel org → Odoo company, role
  → group, Actions-v2 hook for claim injection (memo 04 §6).
- `mcp_pro_governance_siem` — OCSF + CEF exporters.
- `mcp_pro_governance_approvals` (if not already in v0.4).
- Cerbos + OpenFGA PDP adapter samples.

### v1.0 — App Store release (Q4 2026)

- Translations (NL, EN, DE, FR).
- `static/description/index.html` polished.
- Screencasts, auditor-ready evidence pack.
- Submitted to apps.odoo.com.

## 9. Concrete patterns committed

From memo 04 ("Concrete patterns worth stealing"), now promoted to
design rules:

1. **One ULID `request_id` flows end-to-end** — generated by MCP Pro,
   carried as OTel `gen_ai.tool.call.id`, stored as primary key of
   `mcp.audit.event`.
2. **Token audience = `https://{host}/db/{db_name}`** — binds every
   token to a specific Odoo database, not just to the server.
3. **Declared-vs-enforced pairing** — record `destructiveHint` /
   annotation from the tool manifest AND the actual
   `check_access_rights` outcome; mismatch is a governance signal.
4. **`WWW-Authenticate` scope challenges** for scope elevation.
5. **Per-client consent registry** before forwarding to the AS.
6. **HITL via `mcp.approval.request` records** — reuses Odoo approval
   UX.
7. **Audit both allow and deny paths** — denies are the highest-signal
   rows (injection probes).
8. **Narrow PDP interface** — see §6.
9. **Hash-and-store payloads by default**, full capture opt-in and
   sensitivity-label-gated.
10. **Sampling is a capability, not a right** — allow-list per agent.

Plus the three memo 01 patterns worth porting:

11. **Publish-time enforcement** — an agent can't leave `draft` unless
    scope-catalogue coverage, system card, sponsor, and DLP policy
    are all assigned.
12. **Two-owner invariant** — every `mcp.agent` needs ≥2 accountable
    parties from distinct groups to prevent orphaning.
13. **Agent risk score** as a first-class `selection` field
    (low/medium/high), initially populated by local heuristics
    (trifecta trips, deny rate, rate-limit breaches), with a hook for
    external signal (Entra Identity Protection, memo 01).

## 10. Resolved open questions

Issues the memos raised that are now decided:

- **License:** LGPL-3 (memo 03 Q2, memo 06 Q6). Decided.
- **Odoo target:** 18.0+ (memo 03 Q4). Decided.
- **Scope of prompt capture:** hash by default, full capture opt-in +
  sensitivity-labelled (memo 04 Q5, memo 05 Q1, memo 06 Q1). Decided.
- **Audit mutability:** `mcp.audit.event` is strictly append-only;
  `auditlog` is a UX-only echo when present (memo 03 Q5). Decided.
- **Agent-key binding side-table:** yes, to work around
  `res.users.apikeys._auto=False` (memo 03 Q7). Decided.
- **Rate-limit backend:** Postgres default, Redis adapter optional
  (memo 03 Q8). Decided.
- **RFC 9396 from day 1:** no — functional scopes in v0.2–v0.5;
  `authorization_details` accepted but not required (memo 04 Q2).
  Decided.
- **Blueprint vs instance:** collapsed into `mcp.agent` with optional
  `template_id` self-ref (memo 01 Q1). Decided.
- **Standards alignment of schema:** field names on `mcp.audit.event`
  and `mcp.agent` **match Microsoft Entra Agent ID / Purview** where
  there's no Odoo-native naming conflict (memo 06 Q10). Decided —
  makes future federation a mapping, not a rewrite.
- **Memory poisoning:** deferred past v1 (memo 05 §deferred).
  Decided.
- **Tool-description integrity:** deferred (memo 05 §deferred).
  Decided.

## 11. Questions reserved for the first architecture spike

These are genuinely hard and should not be closed now:

1. **`env.agent_uid` thread-local primitive.** Odoo's ORM has no
   second-subject concept. Introducing one (so `mail.message` authored
   by "human via agent" differs from "agent autonomous") ripples into
   every write. Memo 01 Q2 + memo 04 Q6. Needs a proof-of-concept
   before v0.2 lands.
2. **Retention reconciliation.** AI Act 6m vs DORA 5y vs GDPR
   storage-limitation vs right-to-erasure against an immutable log.
   Memo 02 Q2, Q3. Resolution sketch: pseudonymise `principal_chain`
   after 6m (replace `sub` with salted hash), keep the rest 7y,
   honour RTBF via salt-deletion rendering old rows unlinkable.
   Needs legal review before v0.5.
3. **Provider vs deployer under Art. 25(1).** When does a customer's
   tool binding turn them into a provider? Memo 02 Q1, Q5. Conservative
   default: every non-trivial tool binding creates an AIIA entry.
   Needs EU AI Office guidance when it lands.
4. **Multi-tenant boundary** when MCP Pro is multi-tenant but Odoo is
   single-DB. Memo 04 Q7. Canonical URI must be DB-scoped; remaining
   question is how the module surfaces cross-tenant aggregates to
   an MSP operator.
5. **Sponsor transfer** absent `hr.employee` (memo 01 Q4). Proposal:
   lightweight `mcp.agent.sponsor.transfer.policy` with fallback
   rules (company manager, then group manager, then
   `group_mcp_governance_manager`).
6. **Policy-version propagation to live sessions** (memo 03 Q9).
   Options: bump `mcp.agent.policy_version` into every token
   introspection or re-check on every request. Latter is simpler and
   MCP BCP already says "never session-authenticate" (memo 04).
7. **OWASP LLM01 prompt filtering scope.** Memo 04 Q8. Default
   position: the MCP host owns prompt filtering; we own the audit of
   outcomes. Revisit if customer research says otherwise.
8. **Agent risk score algorithm.** Memo 01 Q6. Heuristic v0 —
   weighted recent denies + rate-limit trips + trifecta flags over
   rolling window. Needs empirical calibration on real MCP Pro logs
   before v0.4.

## 12. Non-goals (explicit, to prevent scope creep)

Everything in memo 06 §"Features we should NOT build":

- SAML IDP implementation (use OCA `auth_saml`).
- Keycloak OIDC implementation (use OCA `auth_oauth_keycloak`).
- General RBAC / role template management (integrate OCA
  `base_user_role`).
- Organisation-level AI policy authoring (export to Credo AI /
  Holistic / IBM).
- Model performance / drift / bias monitoring (Fiddler, Arize, W&B).
- DLP of user-side LLM prompts leaving the browser (Purview,
  Netskope, Zscaler).
- EU AI Act / ISO 42001 control framework authoring surface
  (Prismtech GRC, ServiceNow IRM, Credo).

Plus:

- Re-implementing `mail.thread` chatter.
- A new ORM layer for policies.
- A hosted / SaaS variant at this layer (that is `odoo-mcp-pro-admin`'s
  scope).

## 13. What to do next

1. **Wipe and rewrite `mcp_pro_governance/` v0.1 scaffold to v0.2
   schema** (§4.3). Low risk; no external users.
2. **Audit `auth_jwt` 19.0 status and commit to a resolution path
   above** (§3). If OCA port is missing, decide between contributing
   upstream vs vendoring a minimal verifier — either way needs to be
   locked before v0.2 line-of-code #1.
3. **POC the `env.agent_uid` primitive** (§11 Q1). Two-day spike.
4. **Draft the scope catalogue seed** from MCP Pro's current 6 tools
   (§4.1 `mcp.tool.scope`). One afternoon.
5. **Draft the trifecta rule taxonomy** from memo 05 §2 + EchoLeak /
   ForcedLeak analysis. One afternoon.
6. **Start the DPIA + System Card templates** using memo 02 hard
   requirements #5, #6, #8 as skeleton. Can run in parallel with
   code work — these are markdown-first artefacts.
7. **Book legal review** on:
   - LGPL-3 + AGPL-3 soft integration (`auditlog` pointer-only).
   - Retention reconciliation sketch (§11 Q2).
   - Provider-vs-deployer threshold (§11 Q3).

Once the POC and legal review are back, v0.2 implementation can begin
with the 2026-08-02 deadline as the north star for v0.5.

---

## Appendix A — Decision log (condensed)

| # | Decision | Primary memos | Status |
|---|---|---|---|
| D01 | Target Odoo 19.0 (18.0 back-port optional, later) | 03 | Set |
| D02 | License LGPL-3 | 02, 03, 06 | Set |
| D03 | Collapsed `mcp.agent` with optional template | 01, 06 | Set |
| D04 | Side-table `mcp.agent.key`, never ALTER core apikeys | 03 | Set |
| D05 | Append-only `mcp.audit.event` with hash chain | 02, 04, 05 | Set |
| D06 | Pluggable PDP, in-process default | 04 | Set |
| D07 | Lethal-trifecta gate in v0.3 | 05 | Set |
| D08 | HITL approval workflow in Odoo | 04, 02 | Set |
| D09 | Hard dep `auth_jwt`, AGPL deps pointer-only | 03 | Set |
| D10 | Rename v0.1 models before v0.2 ships | 01, 04, 06 | Set |
| D11 | Sub-modules for Zitadel, Enterprise, SIEM | 01, 06 | Set |
| D12 | EU AI Act 2026-08-02 is the v0.5 deadline | 02 | Set |
| D13 | Microsoft-compatible field names on audit + agent | 01, 06 | Set |
| D14 | Memory poisoning + tool-description integrity deferred past v1 | 05 | Set |

## Appendix B — Sources index

All claims in this synthesis trace to one of the six memos; see their
inline citations for primary sources. High-value primaries reused
throughout:

- MCP specification revision 2025-06-18 —
  [authorization](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization),
  [security BCP](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices).
- [Regulation (EU) 2024/1689 — EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng).
- [NIST AI RMF 1.0](https://airc.nist.gov/airmf-resources/airmf/) +
  [NIST AI 600-1 GenAI profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf).
- [ISO/IEC 42001:2023](https://www.iso.org/standard/81230.html).
- [OWASP LLM Top 10 2025](https://genai.owasp.org/) +
  [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/).
- [MITRE ATLAS v5.4.0](https://atlas.mitre.org/).
- [Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/identity/) (preview docs),
  [Purview for AI](https://learn.microsoft.com/en-us/purview/ai-microsoft-purview),
  [RAI Standard v2](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf).
- [Odoo 18 module reference](https://www.odoo.com/documentation/18.0/developer/reference/backend/module.html).

---

**End of synthesis.** Next touch: wipe-and-rewrite the v0.1 scaffold to
the v0.2 schema, and book the legal review in parallel.
