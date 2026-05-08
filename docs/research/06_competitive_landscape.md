# 06 — Competitive Landscape: AI + Data Governance in Enterprise Suites

**Status:** Research memo, informs scoping of `mcp_pro_governance`.
**Date:** 2026-04-24.
**Author:** Pantalytics research.
**Scope:** What the big ERP / business-application suites ship today for AI and data governance, what standalone AI-governance vendors offer, what the Odoo App Store actually contains, and where `mcp_pro_governance` should sit.

The background noise across all of 2026 is that "AI agent governance" has become a buyable line-item from every enterprise vendor. What is actually shipped, what is on a roadmap slide, and what is bundled in a SKU you already own are three very different things. This memo tries to keep them separate.

---

## 1. SAP — Joule and the governance stack

### Joule and its relationship to SAP Build / BTP

Joule is SAP's cross-suite copilot, positioned as the chat-and-agent surface across S/4HANA, SuccessFactors, Ariba, Concur, and Signavio. In 2026 SAP repositioned Joule from "copilot that answers questions" to "agent fabric that executes tasks" — the Joule Studio agent builder became generally available in Q1 2026, letting enterprises design custom agents using SAP business objects as tools ([SAP community Q1/2026 update](https://community.sap.com/t5/technology-blog-posts-by-sap/sap-ux-q1-2026-update-part-1-ai-joule-sap-build-work-zone-sap-mobile-start/ba-p/14312110)).

The authoring surface sits inside SAP Build (the low-code / pro-code platform on BTP). Agents published from Joule Studio register themselves with Joule at runtime. The consumption engine is SAP AI Core; the observability / evaluation UI is SAP AI Launchpad.

### SAP AI Core and AI Launchpad — governance features

SAP AI Core is the runtime that hosts model endpoints and the Generative AI Hub (LLM proxy). AI Launchpad is the operations console: model deployment, prompt registry, evaluation runs, and — as of the H1 2026 release — an agent monitoring tab that shows per-agent tool invocations and token consumption.

What SAP calls "governance" here is mostly four things:
- **Model choice and routing** via the Generative AI Hub (the customer picks which LLM family services which workload).
- **Prompt registry with versioning** — prompts are first-class objects that can be promoted through dev / test / prod.
- **Usage metering via AI Units** — the billing primitive, also used for quota enforcement ([SAP Joule metering and pricing docs](https://help.sap.com/docs/joule/integrating-joule-with-sap/metering-and-pricing)).
- **Grounding scope** — which SAP business objects a given Joule agent is allowed to read.

Missing (still) from AI Launchpad in April 2026: a first-class segregation-of-duties model for agents, and a per-agent audit export that a SOX/ISAE 3402 auditor would sign off on without asking "but where does the prompt come from?".

### Cloud Identity Services — agent identity

SAP Cloud Identity Services (CIS) gained "service user" support for agents in late 2025. Agents registered through Joule Studio get an identity in the Identity Authentication Service (IAS) tenant and are provisioned through the Identity Provisioning Service to downstream apps. This is the closest thing SAP has to Microsoft's Entra Agent ID. It is functional but not yet deeply integrated with Joule's runtime — the linkage between "this Joule agent invoked this tool" and "this service user did this RFC call into S/4" still relies on correlation IDs rather than a single identity propagation chain.

### SAP Integration Suite — audit / observability

Integration Suite's Cloud Integration component writes message-processing logs that can be shipped to SAP Cloud ALM or a customer SIEM. For agent-mediated flows, customers can enable payload logging, but payload retention is deliberately limited (seven days default) for GDPR reasons. Customers building regulated agent workflows tend to front-end this with their own SIEM.

### GA vs roadmap (as of 2026-04)

| Capability | Status |
|---|---|
| Joule chat across SAP apps | GA |
| Joule Studio agent builder | GA (Q1 2026) |
| Custom agent execution free for SAP Build customers | Promo through 2026-05-31 |
| AI Units-based metering | GA |
| Agent service users in IAS | GA (late 2025) |
| Per-agent audit export in AI Launchpad | In ramp-up |
| SoD model for agents | Roadmap; not in public docs |

### Pricing signals

From the SAP pricing page and the metering docs: "Joule Base is included at no additional cost in all SAP Cloud subscriptions" ([SAP Business AI pricing](https://www.sap.com/products/artificial-intelligence/pricing.html)). Advanced capabilities require AI Units. Per the SAP Licensing Experts primer, per-user Joule Premium packages tier from 8 AI Units/user/month down to 1 AI Unit/user/month by volume ([SAP Joule licensing](https://saplicensingexperts.com/blog/sap-joule-licensing-pricing-and-budget-planning.html)). AI Units expire after 12 months.

**Net for Odoo positioning:** SAP's model is "buy the suite, get the governance bundled but coupled." A customer who only uses S/4 finance cannot extract just Joule governance and put it in front of Salesforce. Odoo customers would look at SAP's stack with the same envy they look at SAP pricing: nice but not accessible.

---

## 2. Oracle — AI Agent Studio / OCI Generative AI Agents

### Architecture

Oracle's agent stack has three tiers:
- **OCI Generative AI** (the model endpoints, incl. Cohere Command, Meta Llama, OCI-hosted frontier models).
- **OCI Generative AI Agents** (managed agent service with RAG, tools, and now MCP + A2A support as of the 2026 expansion).
- **AI Agent Studio** (the authoring surface, part of OCI Enterprise AI which went GA in early 2026) ([OCI Enterprise AI GA blog](https://blogs.oracle.com/ai-and-datascience/announcing-oci-enterprise-ai-ga)).

The upgraded Studio "includes support for the Model Context Protocol and Google's Agent2Agent standards, a set of new agent observability and evaluation tools, new prompt and agent-building features and multi-modal and retrieval-augmented generation capabilities" ([AI Business coverage](https://aibusiness.com/agentic-ai/oracle-expands-agentic-ai-platform-with-new-features)).

### IAM for agents in OCI

"You can get access to Generative AI Agents resources with OCI Identity and Access Management (IAM) policies" — Oracle's position is that agents are just another OCI resource type, governed by the same compartments and policies as compute instances ([OCI docs: IAM policies for Generative AI Agents](https://docs.oracle.com/en-us/iaas/Content/generative-ai-agents/iam-policies.htm)).

In practice this means agents run as a dynamic-group principal with policies like `allow dynamic-group my-agents to use generative-ai-agents in compartment X`. The primitive works; the UX of modelling "this agent can read Sales orders but not Purchase orders" still pushes a lot into policy authoring by hand.

### Audit

OCI Audit service records management-plane events for Generative AI Agents (creation, deletion, configuration). Data-plane calls (chat turns, tool invocations) land in OCI Logging, not in Audit. That distinction matters for compliance teams who expect "audit" to mean "every action the agent took against my data." Oracle's own GA blog does acknowledge the gap: "Teams get clearer visibility into how agents behave, what tools they use, and how data moves through interactions."

### Governance claims vs what's in the docs

Marketing: "OCI Enterprise AI Governance provides enterprise-grade security, compliance, and access controls at every stage."
Docs: IAM policies + Audit service for control-plane + Logging for data-plane, all wired through the standard OCI primitives.

This is honest but unexciting: Oracle is not offering a dedicated "AI governance" UI; they are saying "use OCI's governance primitives, which happen to also cover agents."

---

## 3. Microsoft Dynamics 365 + Copilot Studio

This is the most complete governance story of the ERP-adjacent vendors, mainly because Microsoft has been building the plumbing for four years.

### Agent publishing flow

Copilot Studio lets makers build agents that then get published to an environment. The gate is a maker policy, and the runtime enforces Entra ID identity, environment DLP, and Purview sensitivity labels. Every agent gets its own identity in Entra Agent ID — "an identity with access controls, audit trails, and lifecycle management, just like a human employee" ([Windows News: March 2026 Copilot transformation](https://windowsnews.ai/article/microsoft-365-copilots-march-2026-transformation-from-assistant-to-agentic-work-layer-with-governanc.409097)).

### DLP and Purview integration

Copilot agents "respect existing DLP policies automatically" — a prompt that would have the agent share a sensitive doc externally is blocked or rewritten ([Microsoft Learn: DLP for Copilot](https://learn.microsoft.com/en-us/purview/dlp-microsoft365-copilot-location-learn-about)). Purview Audit captures prompt / response telemetry with the standard retention tiers.

### Agent 365

"Agent 365 gives your IT team a single dashboard showing every agent running in the organization, what data each one touches, and whether any are operating outside policy" ([2toLead coverage](https://www.2tolead.com/insights/microsoft-365-copilot-updates-in-2026-whats-new)). GA was flagged for May 2026 at $15 per user/month (bundled in the E7 Frontier Suite at $99 user/month, same source).

### How Dynamics 365 plugs in

Dynamics 365 apps surface Copilot in-app (Sales Copilot, Customer Service Copilot). Custom agents built in Copilot Studio use the Dataverse connector, which honors Dataverse column-level security, record-level security, and field-level auditing. The governance boundary is Dataverse's ACLs + Purview DLP + Entra ID.

**Caveat:** the "agents respect DLP automatically" story assumes the agent uses Microsoft Graph / Dataverse connectors. Agents that call arbitrary external APIs bypass this unless a connector policy blocks that category.

**Comparison anchor:** this is the stack Odoo is structurally furthest from. Microsoft's moat is the identity / labels / audit plumbing that predates the AI hype. Odoo has none of it natively.

---

## 4. Workday — Illuminate and the Agent System of Record

Workday's 2025–2026 narrative is "Agent System of Record" (ASOR): a registry where every agent — Workday-built or third-party — is inventoried, audited, and lifecycled. The ASOR integrates with Microsoft Entra Agent ID for identity federation ([Workday blog](https://blog.workday.com/en-us/workday-delivers-next-wave-agentic-ai-power-new-work-day.html)).

Key features:
- Central inventory with agent metadata, owner, and risk class.
- Usage analytics per agent (tasks run, outcomes, hours saved).
- Access control tied to Workday's domain security framework — "agents adhere to the same strict access controls and compliance standards as human employees" ([PRNewswire release](https://www.prnewswire.com/news-releases/workday-illuminate-expands-with-new-ai-agents-for-hr-finance-and-industry-302557725.html)).
- A Financial Audit Agent that automates evidence collection.

What's credible and what's marketing:
- Credible: the reuse of Workday's existing domain security model for agent authorization is the single most auditor-friendly design choice in the whole vendor landscape. Auditors already know Workday's security schema; extending it to agents is a small stretch.
- Marketing: "agent system of record" presumes third-party agents actually register themselves, which is a standards question (A2A, MCP) not yet settled in production.

---

## 5. NetSuite — OCI Generative AI integration

NetSuite's AI story sits downstream of OCI — SuiteConnect 2025 / 2026 announcements position OCI credits for data enrichment, intelligent document processing, and AI-generated narratives inside financial modules ([NetSuite newsroom](https://www.netsuite.com/portal/company/newsroom/oracle-netsuite-supercharges-the-suite-with-expansion-of-generative-ai-capabilities.shtml), [Futurum SuiteConnect coverage](https://futurumgroup.com/insights/suiteconnect-nyc-will-embedded-intelligence-redefine-erp-value/)).

Specifically announced:
- Intelligent Close Manager dashboard with AI-driven monitoring.
- Generative-AI bank matching.
- AI narratives in inventory, payroll, service.
- The new NetSuite Integration Platform (low-code, AI-driven) — GA in North America, ANZ, and UK/Ireland.

**Governance-specific posture:** basically inherits OCI's governance primitives (IAM, Audit, Logging) for any custom agent workloads, and the NetSuite role-based permissions for in-app AI actions. There is no NetSuite-native "AI control tower" equivalent; the governance is thinner than Oracle Fusion Apps.

---

## 6. ServiceNow — Now Assist and AI Control Tower

ServiceNow has been the loudest "AI governance" voice in the enterprise suite space. The AI Control Tower is a standalone product in the ServiceNow Store; it ships in the Zurich (March 2026) and earlier Yokohama (September 2025) releases.

Zurich capabilities ([ServiceNow Community blog](https://www.servicenow.com/community/grc-blog/servicenow-ai-control-tower-in-the-zurich-release-mastering-ai/ba-p/3365258)):
- Full lifecycle orchestration: intake, risk assessment, pre-deployment review, retirement.
- Third-party model choice and routing: AWS Anthropic, Azure OpenAI, Google Gemini, alongside ServiceNow's own models.
- Allowlist-of-providers governance integrated into Now Assist Skill Kit and AI Agent Studio.
- AI asset workspaces, case tracking for product owners and AI CoE teams.
- Integration with ServiceNow GRC (renamed "ServiceNow Integrated Risk Management") for AI-specific risk and compliance workflows.

Yokohama baseline ([Yokohama release notes](https://www.servicenow.com/docs/r/yokohama/release-notes/ai-governance-rn.html)):
- AI Governance workspace (the product formally entered GA).
- Inventory + policy engine + evaluation against ISO 42001 / EU AI Act control sets.

The Control Tower is the most "AI TRiSM"-shaped thing in the suite vendors' catalogs. ServiceNow is closer to Credo AI's positioning than SAP is.

---

## 7. Salesforce — Agentforce and the Einstein Trust Layer

### What the Trust Layer claims

- **Zero-retention prompt routing** to third-party LLMs — "Salesforce has agreements with LLM providers that include commitments for zero data retention" ([Salesforce Trusted AI page](https://www.salesforce.com/artificial-intelligence/trusted-ai/)).
- **Dynamic grounding** — retrieval scoped by Salesforce's permissions model so the LLM only sees what the user can see.
- **PII masking** prior to LLM call.
- **Toxicity scoring** on responses.
- **Audit trail** — "Everything during the entire prompt-to-response journey is timestamped metadata collected into an audit trail" ([Salesforce Help: Einstein Trust Layer](https://help.salesforce.com/s/articleView?id=sf.generative_ai_trust_layer.htm)).

### Under scrutiny

The published critiques cluster around two themes.

**Walled-garden limitation.** The Trust Layer "is only designed to protect data moving in and out of Salesforce, while company knowledge doesn't live in just one place" ([eesel AI overview](https://www.eesel.ai/blog/salesforce-einstein-trust-layer)). Agents that need Zendesk / Confluence / Google Docs context either leak outside the Trust Layer or get a degraded response.

**Sandbox gaps.** "Some key features are not available for testing in sandbox environments, such as LLM Data Masking configuration within the Einstein Trust Layer setup" (same source). Teams end up validating masking in production, which is a separate compliance problem.

**Agentforce pricing and audit coupling.** Agentforce kept its $2-per-conversation meter and added Flex Credits in 2025 ($500 per 100,000 credits, ~20 credits per action, ~$0.10/action) ([Salesforce Agentforce pricing](https://www.salesforce.com/agentforce/pricing/), [Monetizely commentary](https://www.getmonetizely.com/blogs/the-doomed-evolution-of-salesforces-agentforce-pricing)). Audit and Trust Layer features are included; cost containment isn't.

The Trust Layer is credibly the strongest "data in transit" governance in the SaaS-ERP world. It is not a substitute for (a) agent identity lifecycle management, (b) SoD for agents, or (c) cross-suite inventory.

---

## 8. Standalone AI-governance platforms

The "AI TRiSM" category (Trust, Risk, Security Management — Gartner framing) has a distinct set of vendors. Gartner's 2025 Market Guide for AI Governance Platforms and the AI TRiSM report list the following as representative vendors ([Credo AI Gartner recap](https://www.credo.ai/blog/credo-ai-featured-in-2025-gartner-market-guide-for-ai-trust-risk-and-security-management-ai-trism), [Credo AI market guide page](https://www.credo.ai/gartner-market-guide-for-ai-governance-platforms)):

| Vendor | Primary focus | Overlap with ERP-module scope |
|---|---|---|
| **Credo AI** | Policy governance, regulatory compliance (EU AI Act, NIST AI RMF) | Low overlap — governs AI systems at an org-wide level, not per-ERP-record |
| **Holistic AI** | Regulatory / risk evaluation | Low overlap — same positioning as Credo |
| **Fiddler AI** | Model performance + drift monitoring | None — model-monitoring, not data-access governance |
| **Arize AI** | Model observability | None — same space as Fiddler |
| **Weights & Biases** | MLOps, experiment tracking + AI governance (newer) | None for ERP, some for custom ML pipelines |
| **Fairly AI** | Bias / fairness risk governance | Low overlap |
| **IBM watsonx.governance** | Full-stack AI governance, model catalog, fact sheets | Overlaps with ServiceNow's AI Control Tower, not ERP-agent scope |

Gartner's AI TRiSM framing has four quadrants: AI governance, AI runtime inspection / enforcement, AI application security, information governance for AI. The AGP (AI Governance Platform) sub-category is where Credo / Holistic / IBM sit; Fiddler / Arize are primarily in the AIOps side.

**Scope for `mcp_pro_governance`:** these vendors govern AI *programs* at the enterprise level — which models, which use cases, which risk tier, which policies. They do not govern individual agent actions against an ERP record. The overlap with our scope is small; the positioning risk is real (CIOs may assume they've bought governance when they bought Credo, and not fund ERP-level controls).

---

## 9. Odoo App Store — what exists today

Searched apps.odoo.com across the terms: `governance`, `audit`, `audit log`, `audit trail`, `AI`, `AI agent`, `MCP`, `GDPR`, `compliance`, `SSO`, `SAML`, `OAuth`, `API key`, `role`, `RBAC`, `Zitadel`, `Keycloak`, `OIDC`. Selected relevant listings as of 2026-04-24.

### MCP-focused modules

| Module | Publisher | Versions | Price | Notes |
|---|---|---|---|---|
| [Odoo MCP Studio](https://apps.odoo.com/apps/modules/19.0/odoo_remote_mcp) | Codemarchant | 19.0 | €299.00 | AI React app / module / dashboard builder over remote MCP |
| [Odoo MCP Server (PRO)](https://apps.odoo.com/apps/modules/19.0/mcp_server_odoo) | KSRO Labs | 19.0 | €210.00 | Claude / ChatGPT / Gemini connector; mentions audit logs |
| [MCP Server](https://apps.odoo.com/apps/modules/17.0/mcp_server) | Andrey Ivanov | 17.0 | €99.00 | MCP connector, minimal governance |
| [MCP Server — AI Integration Hub](https://apps.odoo.com/apps/modules/19.0/pt_odoo_mcp_server) | Niyu Labs | 19.0 | €86.21 | "Governed access" phrasing, minimal actual governance primitives |
| MCP Server (XFanis) | XFanis | 19.0 | €0.85 | Claims native ACL, audit trail, rate limiting, IP filtering |
| [Sadeem MCP](https://apps.odoo.com/apps/modules/19.0) | Sadeem Cloud | 19.0 | €20.00 | Basic Claude <-> Odoo connector |
| [Odoo AI Agent (MCP & Copilot)](https://apps.odoo.com/apps/modules/19.0/odoo_ai_mcp) | — | 19.0 | — | In-app agent + MCP |
| [Claude Integration](https://apps.odoo.com) | RAG Solutions | — | €75.00 | "Trains" Claude against Odoo via MCP |

Observation: nobody in this set ships a first-class *agent identity* model, SoD conflict detection, or federated identity for agents. The most governance-adjacent claim is XFanis's ACL + rate limiting + IP filter combo, which is session-layer, not identity-layer.

### Audit / RBAC / access-control modules

| Module | Publisher | Versions | Price | Notes |
|---|---|---|---|---|
| [GRC — Risk Management — Compliance](https://apps.odoo.com/apps/modules/19.0) | Prismtech | 19.0 | €2,000.00 | Full GRC: NIS2, DORA, ISO 27001, GDPR controls |
| [Advanced User Audit](https://apps.odoo.com/apps/modules/17.0/advanced_session_management) | Terabits Technolab | 17.0 / 19.0 | €170.06 | Session, login, activity tracking |
| [Audit Log](https://apps.odoo.com/apps/modules/16.0/zehntech_auditlogs) | Zehntech | 16.0+ | varies | CRUD logging |
| [Field Tracker](https://apps.odoo.com/apps/modules/19.0) | Odoo Hub | 19.0 | €30.00 | Field-level change tracking to chatter |
| [Role-Based Access Control (RBAC) Manager](https://apps.odoo.com/apps/modules/18.0/rbac_manager) | — | 18.0 | — | Role templates, risk-classified permissions |
| [access_roles](https://apps.odoo.com/apps/modules/18.0/access_roles) | — | 18.0 | — | Basic role wrapper |
| [Advanced Access Control](https://apps.odoo.com/apps/modules/19.0) | TechUltra Solutions | 19.0 | €38.51 | Hide chatter, dev mode, buttons, menus |
| [Odoo Access Control Management](https://apps.odoo.com/apps/modules/17.0/access_control_management) | — | 17.0 | — | Menu / action restriction |
| [AI Smart Actions](https://apps.odoo.com/apps/modules/19.0) | Orionyx | 19.0 | €170.32 | Interesting: AI record creation with allowlists, quotas, audit trails |

Observation: the RBAC layer is well-covered (especially by OCA's `base_user_role` discussed in memo 03), and audit modules are plentiful but fragmented. What does not exist is a module that unifies agent identity + key scope + audit record + SoD signal.

### SSO / identity federation

| Module | Publisher | Versions | Price | Notes |
|---|---|---|---|---|
| [auth_saml](https://apps.odoo.com/apps/modules/13.0/auth_saml) | OCA | many | Free | OCA SAML module — the reference implementation |
| [SAML SSO (miniOrange)](https://apps.odoo.com/apps/modules/17.0/miniorange_saml_sp_20) | miniOrange | 17.0 | €431.62 | Azure AD, Okta, ADFS, Keycloak, Ping, OneLogin, GSuite |
| [Okta SSO for Odoo](https://apps.odoo.com/apps/modules/16.0/cr_okta_login) | — | 16.0+ | varies | OAuth + MFA |
| [Microsoft Azure SSO](https://apps.odoo.com) | Serpent Consulting / Softhealer / Webkul | 17.0+ | €76–€129 | Three overlapping Azure SSO modules |
| [auth_oauth_keycloak](https://apps.odoo.com/apps/modules/14.0/auth_oauth_keycloak) | OCA | 14.0+ | Free | Keycloak OIDC |
| [Login with OneLogin / Apple](https://apps.odoo.com) | echoBitz | 17.0+ | €24–€33 | Narrow IDPs |

Observation: no Zitadel-specific module exists in the app store. Keycloak is covered via OCA's `auth_oauth_keycloak`. A generic OIDC connector exists but is not positioned for agent-token flows.

### OCA modules — publishing pattern

OCA's relevant modules (`auth_saml`, `auth_oauth_keycloak`, `auditlog`, `base_user_role`, `mail_tracking`, `ir_audit_trail`, etc.) are mostly published to `github.com/OCA` and `apps.odoo-community.org`, with a subset also listed on apps.odoo.com under the OCA account. Coverage on apps.odoo.com is incomplete: `auditlog` is there up to 12.0 / 15.0 with gaps; `base_user_role` is typically only on the OCA shop, not apps.odoo.com.

Practical implication: customers who browse apps.odoo.com rather than OCA's shop will *not* see the most credible free governance modules. That's white space for a consolidated, well-listed governance module.

---

## 10. Adjacent Odoo-world offerings

### Odoo's own AI story (18 → 19)

From the Odoo 19 release notes ([odoo.com/odoo-19-release-notes](https://www.odoo.com/odoo-19-release-notes)):
- AI agents can "chat, learn from documents, and perform actions" against database records.
- AI-powered natural-language search over records.
- Draft emails, improve text, summarise chatter.
- Customer can use their own Gemini / ChatGPT 5 / Claude account.
- "Light audit trail" available by default (a meaningful but thin default).
- Separated product management access rights; new "Officer" role for attendance; tracked access-right changes in Documents.

On Odoo.sh, vibe coding tools (AI-assisted module generation) went live in February 2026, per Fabien Pinckaers.

Observation: Odoo is shipping AI *consumption* features fast, governance features slowly. The "light audit trail" default is the first meaningful step, but there is no concept of an agent identity distinct from a user's API key.

### Third-party Odoo + AI vendors

Visible publishers working this space:
- **KSRO Labs** (MCP Pro, listed above).
- **Niyu Labs** (AI Analyst Chatbot, MCP Server, AI-to-SQL).
- **Webkul** (documentation-centric MCP server).
- **Bista Solutions** (Odoo AI Agent, free).
- **Atharva** (Odoo AI Assistant, €218).
- **Codemarchant** (MCP Studio).
- **Softhealer** (InsightMate AI dashboards).
- **Techspawn** (Turbo AI Agent, free).

Only Niyu Labs explicitly uses the word "governed" in its copy; nobody ships what would survive an ISAE 3402 auditor's "show me the agent inventory" question.

### Pantalytics' own products (self-positioning)

- **MCP Pro** — the MCP server that exposes Odoo to agents. Open-source core on GitHub (`pantalytics/odoo-mcp-pro`), cloud variant at pantalytics.com ([Pantalytics MCP page](https://www.pantalytics.com/en/apps/odoo-mcp-server/)). 6 tools (search, get, create, update, delete, list models), 4 resources, OAuth 2.1 for multi-user cloud, 480+ unit tests.
- **AI Pro** — agentic AI layer on top of MCP Pro for B2B sales / support workflows (per pantalytics.com positioning).
- **Outlook Pro** — bridges Exchange / Entra / Outlook with Odoo so employees stay in their email client.
- **`mcp_pro_governance`** (this repo) — the governance module that sits alongside MCP Pro. Open-source. Agent identity, scoped keys, audit with prompt hash, SoD signal, optional Zitadel hook.

The positioning is: MCP Pro lets AI talk to Odoo; `mcp_pro_governance` lets an auditor sign off on that.

---

## 11. Positioning map

### Axes

- **Enterprise suite native vs bolt-on.** Suite-native means "ships with SAP / Dynamics / ServiceNow and is entangled with their identity + audit plumbing." Bolt-on means "installable module / platform that extends an existing app."
- **AI-first vs ERP-first.** AI-first means "designed around the agent lifecycle, LLM routing, model catalog." ERP-first means "designed around records, permissions, SoD, audit trails, with AI layered on."

### Map

| | ERP-first | AI-first |
|---|---|---|
| **Suite-native** | SAP Joule governance, Oracle AI Agent Studio, NetSuite AI, Dynamics 365 + Copilot Studio, Workday ASOR, Salesforce Einstein Trust Layer | ServiceNow AI Control Tower (purpose-built for AI ops) |
| **Bolt-on** | `mcp_pro_governance`, OCA `auditlog` + `base_user_role`, Odoo app-store RBAC / audit modules, GRC module (Prismtech) | Credo AI, Holistic AI, IBM watsonx.governance, Fiddler, Arize |

### Where `mcp_pro_governance` sits and why

Bottom-left: bolt-on + ERP-first. The thesis:
- Customers who already picked Odoo won't buy SAP Joule governance. They need something installable.
- Odoo admins think in records, ACLs, SoD, audit. Starting there means the module feels like native Odoo, not like a TRiSM console bolted on.
- The AI-first TRiSM vendors (Credo, Holistic, IBM) are complementary, not competitive — they answer "is this model allowed at this risk tier?", we answer "did this agent identity actually follow the Odoo-level rules when it fired 5,000 calls an hour?".

---

## White space in the Odoo ecosystem

Concrete capabilities that nobody ships today for Odoo:

1. **First-class agent identity** — separate from `res.users`, with lifecycle, owner, classification, scope. Every module that exists today collapses agent identity into "just another user's API key."
2. **SoD conflict detection for agents.** One or two modules detect SoD on *users*; none model the case where an agent inherits conflicting grants through two keys.
3. **Prompt-linked audit.** Audit modules record field changes; none record which prompt / request-id / tool-call produced them. This is the line between "we have chatter" and "we have something an auditor accepts."
4. **Scoped MCP/API keys with rate limits, expiry, and rotation SLOs.** Odoo's built-in `res.users.apikeys` has none of this.
5. **Agent-issued OIDC tokens (Zitadel / Entra agent-id compatible).** Several SSO modules for *users*; none for agent-issued tokens.
6. **SIEM-friendly audit export** (JSON Lines, CEF, or OCSF). All the existing audit modules target in-app browsing, not log shipping.
7. **"Governance readiness" report** — the one-page export a SOC 2 / ISAE 3402 auditor actually asks for.

This is the list we should build against.

## Competitive risks to our positioning

Ordered by plausibility of them occupying this space before we do:

1. **Odoo SA itself.** They already shipped a "light audit trail" in 19. A v20 roadmap line item for "agent inventory + scoped keys" would be credible and would compress our window. Mitigation: open-source, move first, become the de-facto reference before Odoo SA has a reason to build.
2. **OCA `auditlog` + `base_user_role` maintainers.** Technically the most qualified people to build this. Mitigation: build as OCA-compatible, contribute upstream where the primitive already belongs in OCA.
3. **KSRO Labs and Niyu Labs.** They both have MCP modules listed. Niyu's "governed access" copy suggests they see the space. Mitigation: open-source + better auditor story. Their products are paid, ours is free at the core.
4. **Credo AI / Holistic AI Odoo connector.** Possible but unlikely — these vendors historically don't ship per-ERP connectors; they consume metadata through CSV / API. If they did, it would be complementary rather than substitutive.
5. **A generic "MCP security proxy" (Pangea, Traceable, Clutch).** Plausible: could eat the session-layer portion of our scope (rate limits, IP filter). Mitigation: focus on Odoo-native primitives (models, ACLs, SoD) that a generic proxy can't see.

## Features we should NOT build because someone else does them better

| Area | Better-elsewhere vendor | What we should do instead |
|---|---|---|
| SAML IDP integration | OCA `auth_saml`, miniOrange | Depend on OCA `auth_saml`, document Zitadel recipe |
| Keycloak OIDC | OCA `auth_oauth_keycloak` | Same — depend, don't re-implement |
| General RBAC / role templates | OCA `base_user_role`, paid RBAC Manager | Integrate; provide SoD overlays, don't own roles |
| Organization-level AI policy (model allow-lists, risk tiers) | Credo AI, Holistic AI, IBM watsonx.governance | Export JSON to these tools; don't reinvent policy authoring |
| Model performance / drift monitoring | Fiddler, Arize, W&B | Out of scope entirely |
| DLP across suites | Microsoft Purview, Netskope, Zscaler | Out of scope — we govern Odoo access, not user-side LLM prompts |
| EU AI Act / ISO 42001 control framework authoring | Prismtech GRC module, Credo AI, ServiceNow IRM | Provide evidence inputs; don't own the framework |

The consolidated rule: we own what sits between the agent and Odoo's records. We do not own what sits between the agent and the LLM, and we do not own the enterprise policy authoring surface.

## Open questions for synthesis

1. **Scope of "prompt" capture.** Store prompt hash only, or the full prompt behind a feature-flag with retention policy? Privacy / GDPR implications vs auditor utility.
2. **Agent identity model: one-to-one with API key, or one-to-many?** One-to-many is more flexible but makes key revocation semantics harder.
3. **Do we integrate with OCA `base_user_role` directly, or define a lightweight role facade so non-OCA deployments work too?**
4. **Zitadel vs generic OIDC first.** Zitadel is the anchor partner; generic OIDC is the broader story. Which documentation path is primary?
5. **SIEM export format.** OCSF (newer, CrowdStrike-backed) vs CEF (older, universally accepted) vs both.
6. **Licensing.** LGPL-3 (viral-lite, OCA-compatible) vs AGPL-3 (matches Odoo core). Implications for adoption by paid-App-Store competitors who might otherwise absorb us.
7. **Audit retention.** Default in-DB retention window, archive to object storage, or leave retention to the customer's SIEM?
8. **How aggressively should we publish to apps.odoo.com** vs keeping the primary distribution on GitHub + OCA? Apps.odoo.com listing discovery is high but friction for quick updates.
9. **Relationship with Odoo SA's "light audit trail."** Do we extend it (hook into the same chatter conventions) or replace it for agent-sourced events?
10. **Standards alignment.** Should agent identities be expressed to match Microsoft's Entra Agent ID schema for future federation, or keep an Odoo-native schema and map at export time?

---

*End of memo 06.*
