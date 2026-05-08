# 01 — Microsoft Reference Architecture for Agentic AI Governance

Research memo for `mcp_pro_governance` (Odoo module). The goal is to extract the
precise primitives Microsoft exposes for governing AI agents in the enterprise so
we can decide what to port, what to reinterpret for an ERP context, and what to
leave out.

Unless otherwise noted, status labels (GA / Preview / Announced) reflect the state
of the products as documented on `learn.microsoft.com` between late 2025 and
2026‑04‑24. Several of these primitives are **Preview** — useful conceptually
but not yet safe to treat as a stable contract.

---

## Entra ID — Agent Identity

Microsoft's top‑level construct is **Microsoft Entra Agent ID** (Preview, surfaced
through the Microsoft 365 "Frontier" program). Microsoft explicitly models agents
as a **new class of identity**, distinct from both human users and workload
(service principal) identities. The motivation stated on Microsoft Learn is that
existing identity models "prove insufficient" for AI agents because agents are
"created dynamically", may "exist for minutes during a specific task, or might be
created and destroyed thousands of times per day", and must be
"distinguish\[ed\] … from operations performed by workforce, customer, or
workload identities" ([What are agent identities?](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/what-is-agent-id)).

### The four object types

Microsoft decomposes "agent identity" into **four** directory objects, which is
the most important schema choice in the whole stack
([Conditional Access for Agent Identities](https://learn.microsoft.com/en-us/entra/identity/conditional-access/agent-id)):

| Object | Definition (MS Learn) | Role |
| --- | --- | --- |
| **Agent blueprint** | "A logical definition of an agent type." | Template; the "kind" of agent. |
| **Agent identity blueprint principal** | "A service principal that represents the agent blueprint in the tenant and executes only creation of agent identities and agent users." | Holds the credentials; creates children. |
| **Agent identity** | "Instantiated agent identity. Performs token acquisitions to access resources." | The runtime actor. |
| **Agent user** | "Nonhuman user identity used for agent experiences that require a user account. Performs token acquisitions to access resources." | Optional 1:1 companion account for UI systems that expect a user. |
| **Agent resource** | "Agent blueprint or agent identity acting as the resource app (for example, in agent to agent (A2A) flows)." | The same object in the audience role. |

Blueprints "establish\[…\] the kind of agent and record\[…\] metadata shared
across all agent identities of a common kind", and let the admin "apply a
conditional access policy to all Sales Assistant Agents", "disable all Sales
Assistant agents", or "revoke a permission grant for all Sales Assistant agents"
([Overview of agent identities](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/agent-identities)).

### Attributes on an agent identity

The documented "anatomy" of a single agent identity is ([source](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/agent-identities)):

- **Identifier** (`id`, object ID, e.g. `aaaaaaaa-1111-2222-3333-…`)
- **Display name** ("surfaced in … Microsoft Entra admin center, Azure portal,
  Teams, Outlook, and more")
- **Sponsor** — "records the human user or group that's accountable for an
  agent. This sponsor is used for various purposes, such as contacting a human in
  case a security incident happens." (Note: distinct from *creator*; if the
  sponsor leaves, "sponsorship of the agent identities is automatically
  transferred to their manager" — see
  [Governing Agent Identities](https://learn.microsoft.com/en-us/entra/id-governance/agent-id-governance-overview).)
- **Blueprint** (the template it was instantiated from)
- **Agent's user account** — optional 1:1 companion user
- **Credentials** — explicitly *none on the agent identity itself*: "Agent
  identities don't have credentials of their own. They rely on the agent identity
  blueprint to acquire tokens on their behalf."
- **Custom security attributes** — arbitrary key/value tags (e.g. an attribute
  set `AgentAttributes` with a multi‑valued attribute `AgentApprovalStatus ∈
  {New, In_Review, HR_Approved, Finance_Approved, IT_Approved}`) usable as CA
  targeting criteria ([CA for Agent ID, scenario 1](https://learn.microsoft.com/en-us/entra/identity/conditional-access/agent-id)).

Credentials on the **blueprint principal** are explicitly enumerated as:

- Federated identity credentials (FIC)
- Certificates / cryptographic keys
- Client secrets

"Credentials do *not* reside on the agent identity."

### Authorization shape

Three token shapes are called out:

1. **Autonomous access** — the subject of the access token *is* the agent
   identity.
2. **Delegated access** — subject is a user, "while the actor is the agent
   identity" (a dedicated `actor` claim; this is the primitive that lets audit
   logs tell a human from an agent acting for that human).
3. **Incoming token validation** — the agent identity acts as the *audience*
   ("agent resource") for A2A calls.

Tokens are tenant‑scoped: "Agent identities can only be issued tokens in the
Microsoft Entra tenant where they're created."

### Provisioning, review, rotation, decommission

Agent identity lifecycle hooks into the existing Entra ID Governance machinery
([Governing Agent Identities](https://learn.microsoft.com/en-us/entra/id-governance/agent-id-governance-overview)):

- **Provisioning**: blueprint creates agent identities; can be triggered from
  Copilot Studio, Microsoft Foundry (which "automatically provisions and manages
  agent identities throughout the agent lifecycle"), Teams Developer Portal, App
  Service/Functions, or Graph API.
- **Access assignment**: via **access packages** in Entitlement Management. The
  policy flag on access package assignment is literally
  **"For users, service principals, and agent identities in your directory"**,
  with a sub‑option **"All agents (preview)"**. Access packages can grant:
  - Security group memberships
  - Application OAuth API permissions (including Graph application permissions)
  - Microsoft Entra roles
- **Request paths**: the agent itself can call
  `POST /identityGovernance/entitlementManagement/assignmentRequests`; or the
  sponsor can request on the agent's behalf; or an admin can assign directly.
- **Review/rotation**: access packages carry expiry; "as the expiry date
  approaches, the sponsor receives notifications about the pending expiration …
  two options: they can request an extension … or they can allow the access
  package assignment to expire." Lifecycle Workflows can automate notifying
  cosponsors/managers on sponsor changes.
- **Decommission**: from the **My Account** portal, sponsors/owners can
  "enable and disable the agent". Agents are designed "for scale and ephemerality
  rather than permanence" so retirement must "not leav\[e\] orphaned credentials
  or permission assignments behind" — a design assertion worth replicating.

### Conditional Access signals for agents

CA for Agent ID (Preview) is applied on **token acquisition**, not on resource
calls. The documented signals and levers ([CA for Agent Identities](https://learn.microsoft.com/en-us/entra/identity/conditional-access/agent-id)):

| Policy component | Values |
| --- | --- |
| **Assignments (scope)** | All agent identities in tenant; specific agent identity by object ID; agents by custom security attributes; agents grouped by blueprint; all agent users. |
| **Target resources** | All resources; all agent resources (blueprints and agent identities — used for A2A); resources by custom security attribute; specific `appId`; specific blueprint (cascades to child agent identities). |
| **Conditions** | `Agent risk` ∈ {High, Medium, Low} (signals from **Microsoft Entra ID Protection** for agents). |
| **Access controls** | `Block` (only grant control exposed in the Preview). |
| **Policy state** | On / Off / Report‑only. |

CA does **not** apply to the blueprint's Graph call that *creates* the agent
identity, nor to intermediate token‑exchange hops at the
`AAD Token Exchange Endpoint`. In the sign‑in logs, agent events are
distinguished by an `agentType` field (`agent user` vs `agent ID user`), and
agent‑identity flows appear under **Service principal sign‑ins** while
agent‑user flows appear under **Non‑interactive user sign‑ins**.

> Status: **Preview** (labeled `agent-id-ignite` and rolling through early 2026;
> Conditional Access for Agent ID page last updated 2026‑04‑21).

### Takeaways for `mcp_pro_governance`

The Entra model gives us the cleanest mental model in the industry right now,
and the clearest evidence that the right decomposition is **blueprint → identity
→ (optional) user companion**, with **sponsor** as a first‑class, mandatory,
transferable attribute *separate from creator*. Credentials live on the template,
not the instance — this lets us rotate a whole fleet at once.

---

## Microsoft Purview for AI

Purview is Microsoft's data‑plane governance layer. The AI offering fans out
from one "front door" surface (**DSPM for AI**) into existing Purview solutions
(DLP, Audit, Sensitivity Labels, Communication Compliance, Insider Risk,
Data Lifecycle Management, Compliance Manager, eDiscovery) all retargeted at
prompts, responses, and AI app inventory ([Purview data security and compliance
protections for M365 Copilot](https://learn.microsoft.com/en-us/purview/ai-microsoft-purview)).

Microsoft explicitly groups in‑scope AI apps into three buckets — a taxonomy we
should probably mirror:

| Bucket | Examples |
| --- | --- |
| **Copilot experiences and agents** | M365 Copilot, Security Copilot, Copilot in Fabric, Copilot Studio |
| **Enterprise AI apps** | Entra‑registered AI apps, ChatGPT Enterprise, Microsoft Foundry |
| **Other AI apps** | Third‑party gen‑AI sites discovered through browser/endpoint telemetry (ChatGPT, Gemini, DeepSeek, consumer Copilot) |

### DSPM for AI

A "classic" DSPM for AI is GA; a new unified **Data Security Posture Management
(preview)** is rolling out worldwide between December 2025 and early May 2026,
with Purview for agents (DSPM‑AI Observability + Insider Risk for AI) reaching
GA by **late May 2026** ([DSPM for AI](https://learn.microsoft.com/en-us/purview/dspm-for-ai);
Microsoft community blog on GA). It inventories and raises signals on:

- **Apps and agents inventory** — per‑agent dashboard "view\[ing\] details about
  sensitive data that they accessed and how they are protected by policies from
  Microsoft Purview."
- **AI activity** — prompt/response counts, sensitive info types surfaced in
  prompts, web‑query references, web search via Bing
  (`AISystemPlugin.Id = BingWebSearch`), jailbreak attempts, cross‑prompt
  injection detections.
- **Oversharing risk** — "default data risk assessment automatically runs
  weekly for the top 100 SharePoint sites based on usage", with remediation
  actions: `Restrict access by label`, `Restrict all items`,
  `Create an auto-labeling policy`, `Create retention policies`. Fabric has an
  equivalent assessment for Dashboard/Report/DataExploration/DataPipeline/
  KQLQuerySet/Lakehouse/Notebook/SQLAnalyticsEndpoint/Warehouse items.
- **One‑click policies**, including *Detect risky interactions in AI apps*,
  *Discover and govern interactions with ChatGPT Enterprise*,
  *Detect sensitive info shared with AI via network* (SASE/SSE integration),
  *Secure interactions for Microsoft Copilot experiences*.

### DLP for AI prompts and responses

Two distinct DLP surfaces exist:

1. **DLP for the Microsoft 365 Copilot "location"** — policy scope is
   "Microsoft 365 Copilot and Copilot Chat". Policies can:
   - **Block web search as a grounding source** when a prompt contains Sensitive
     Information Types (SITs) such as credit‑card numbers, passport numbers, or
     custom SITs; Copilot continues answering from internal data.
   - **Exclude labeled files/emails from response summarization** when they
     carry specified sensitivity labels
     ([DLP for M365 Copilot](https://learn.microsoft.com/en-us/purview/dlp-microsoft365-copilot-location-learn-about)).
2. **Endpoint DLP for third‑party gen‑AI sites** — warn or block users from
   "sharing sensitive information with third‑party generative AI sites that are
   accessed via a browser. For example, a user is prevented from pasting credit
   card numbers into ChatGPT."

New RBAC roles introduced for this surface:

- **Entra AI Admin** — manages M365 Copilot + AI‑related enterprise services
- **Purview Data Security AI Admin** — edits DLP for Copilot and views AI
  content in DSPM for AI

### Audit — schema, retention, export

Prompts and responses are "captured in the unified audit log". Microsoft
publishes a concrete schema ([Audit logs for Copilot and AI apps](https://learn.microsoft.com/en-us/purview/audit-copilot)).
Selected fields worth copying:

| Field | Purpose |
| --- | --- |
| `RecordType` | `CopilotInteraction` (Microsoft Copilot), `ConnectedAIAppInteraction` (third‑party AI deployed and Entra‑registered in your tenant), `AIAppInteraction` (third‑party AI not deployed in your tenant, detected via browser/network DLP). |
| `Workload` | `Copilot`, `ConnectedAIApp`, `AIApp` |
| `Operation` | e.g. `CopilotInteraction`, `ConnectedAIAppInteraction`, `AIAppInteraction`, `UpdateTenantSettings`, `CreatePlugin`, `DeletePlugin`, `EnablePromptBook`, … |
| `AppIdentity` | `workloadName.appGroup.appName`, e.g. `Copilot.Security.SecurityCopilot`, `Copilot.Studio.<AppId>`, `ConnectedAIApp.Entra.<AppId>`, `AIApp.SaaS.<AppName>`. |
| `AppHost` | Hosting surface — `BizChat`, `Bing`, `Office`, `Word`, `Excel`, `Teams`, `Defender`, `Microsoft Purview`, `Security Copilot Standalone`, etc. |
| `AgentId` | e.g. `CopilotStudio.Declarative.<guid>` or `CopilotStudio.CustomEngine.<guid>`. |
| `AgentName`, `AgentVersion` | Friendly name + semver / GUID version. |
| `Messages[]` | Per turn: `ID`, `isPrompt` (bool), `JailbreakDetected` (bool). |
| `AccessedResources[]` | Per grounded document: `ID`, `Name`, `Type`, `SiteUrl`, `ListItemUniqueId`, `SensitivityLabelId`, `Action` (`read`/`create`/`modify`), `Status` (`success`/`failure`), `XPIADetected` (cross‑prompt injection attack detected on that source), `PolicyDetails` (PolicyId, PolicyName, rules, when a DLP policy restricted access). |
| `AISystemPlugin` | Plugin name, ID, version used in the turn (e.g. `BingWebSearch`). |
| `ModelTransparencyDetails` | `ModelProviderName`, `ModelName`, `ModelVersion`. |
| `Contexts[]` | Where the interaction happened — file ID/Teams meeting/channel/chat ID. |
| `AppIdentity` + `CapacityId` | Lets you attribute Fabric usage to a capacity. |
| `ClientRegion` | User region at the time of the operation. |

Retention: Microsoft Copilots are included in **Audit (Standard)**. Third‑party
AI app audit (`AIApp` / `AIAppInteraction`, some `ConnectedAIAppInteraction`) is
**pay‑as‑you‑go**, retained **180 days**, and must be explicitly enabled.

Export: Purview portal Audit search with filters by `Operation`/`RecordType`/
`Workload`; offline filter on `AppIdentity`. Events also flow to **Activity
Explorer** in DSPM for AI (the "AI activities" tab in the new DSPM).
Communication Compliance, eDiscovery, and Data Lifecycle Management all treat
prompts/responses as indexed content in the user's mailbox.

### Sensitivity labels propagating into Copilot

Microsoft's claim is that labels on source content flow through into responses
([Purview AI protections](https://learn.microsoft.com/en-us/purview/ai-microsoft-purview)):

- For encrypted labeled content, users must have the **EXTRACT** usage right
  (not just VIEW) for AI apps to return the data.
- The **highest** sensitivity label of grounding sources is shown in the
  response UI (in Copilot Studio: "the highest sensitivity label applied to
  sources used in the agent's response and individual reference labels in the
  chat").
- S/MIME emails and password‑protected documents are explicitly excluded from
  Copilot grounding.
- `SensitivityLabelId` is on every grounded resource in the audit record, so
  downstream systems can reason over label fan‑out.

### Communication Compliance & Insider Risk for AI

- **Communication Compliance** adds a template to "detect for generative AI
  interactions" — it treats prompts and responses as communications to scan for
  regulatory, harassment, and adult‑content violations, with pseudonymization
  and role‑based access by default.
- **Insider Risk** has a **Risky AI usage** policy template that "detect\[s\]
  risky usage that includes prompt injection attacks and accessing protected
  materials". Signals flow into Defender XDR as AI‑related incidents.

---

## Defender for Cloud Apps — AI posture

Microsoft Defender for Cloud Apps (MDA) plays two distinct roles for AI
governance:

### 1. Shadow AI discovery (GA)

- The cloud app catalog contains **30,000+ apps** scored on **~90 risk
  factors**. The `Generative AI` category is the filter used to surface AI
  traffic. Discovery is performed through Defender for Endpoint telemetry on
  onboarded devices, or via uploaded log files from proxies/firewalls.
- Governance states applied to a discovered app
  ([Manage generative AI apps for your organization](https://learn.microsoft.com/en-us/copilot/microsoft-365/manage-generative-ai-apps)):

  | Tag | Effect |
  | --- | --- |
  | **Sanctioned** | "Officially blesses an application as an approved, corporate standard that is trusted." |
  | **Unsanctioned** | Marked as prohibited. "When an app is marked as unsanctioned, it's automatically blocked across devices that are onboarded to Defender for Endpoint." |
  | **Monitored** | "Marks cloud apps as risky for use" — with MDE integration, users get a warning/educate page when accessing. |

- App‑governance policies use a template‑free custom policy filtered by
  `Category equals Generative AI` with optional `Tag equals Unsanctioned`, and
  apply to "all continuous reports".

### 2. Session controls / reverse‑proxy for AI

Conditional Access App Control (MDA's reverse‑proxy session layer) can be
applied to Entra‑registered AI apps to enforce session‑time controls — block
upload/download of specified categories (e.g. PII patterns), inject warnings,
or redact. For agents, this is the pattern that catches prompt exfiltration via
the UI when DLP‑at‑rest isn't enough.

### 3. AI‑specific alerts via Defender XDR

Defender XDR (Preview as of 2026) adds runtime detection for Copilot Studio and
Microsoft Foundry agents
([Detect, block, and investigate threats to AI agents](https://learn.microsoft.com/en-us/defender-xdr/security-for-ai/ai-agent-detection-protection)):
"Microsoft Defender treats every tool invocation as a high‑value, high‑risk
event, and monitors it in real time" and can **block the tool call** in line
without changing the agent's orchestration. Starting **2 Feb 2026**, Defender
for AI Services covers Foundry‑built agents end‑to‑end. Recurring alert types
include prompt injection, sensitive data exfiltration, risky tool chaining, and
jailbreaks, all materialized as XDR incidents that can pivot into Security
Copilot.

---

## Copilot Studio governance

Copilot Studio is Microsoft's low‑code agent‑authoring surface and is governed
through the **Power Platform** control plane rather than a new bespoke plane.
Every Copilot Studio concept ultimately reduces to a Power Platform primitive
(environment, connector, data policy, maker role)
([Security and governance — Copilot Studio](https://learn.microsoft.com/en-us/microsoft-copilot-studio/security-and-governance);
[Configure data policies for agents](https://learn.microsoft.com/en-us/microsoft-copilot-studio/admin-data-loss-prevention)).

### Environment strategy

- **Environment** is the unit of isolation for DLP, data residency, CMK,
  Managed Environments features, and ALM pipelines. "DLP policies … are applied
  at the environment level, meaning the same agent definition can behave very
  differently depending on where it is deployed."
- Admins configure **environment routing** so makers land in a default
  sandbox/dev environment automatically.
- **Maker welcome message** can be enforced per environment to surface privacy
  and compliance requirements on first use.
- **Customer‑Managed Keys (CMK)** can be attached per environment; **Customer
  Lockbox** is supported (with the explicit carve‑out that "the configured
  Lockbox doesn't cover data sent out from Copilot Studio as part of the
  Agent 365 security audit logging").

### Data policies (DLP) for agents

Enforcement is **real‑time** at publish time. Since early 2025, enforcement is
mandatory: "Agent data policy enforcement exemption is no longer supported.
Agents that were previously exempted from data policy enforcement are all
subject to enforcement."

Every governable capability is modeled as a **connector** put into one of three
data groups:

- **Business**
- **Non‑business**
- **Blocked**

"Connectors must be in the same data group because data can't be shared among
connectors that are in different groups." The set of connectors the admin can
put in a data group is the actual governance surface:

| Capability gated | Connector name |
| --- | --- |
| Agent requires Entra auth | `Chat without Microsoft Entra ID authentication in Copilot Studio` (block to force auth) |
| SharePoint/OneDrive as knowledge | `Knowledge source with SharePoint and OneDrive in Copilot Studio` (endpoint filtering supported) |
| Public websites as knowledge | `Knowledge source with public websites and data in Copilot Studio` |
| Documents as knowledge | `Knowledge source with documents in Copilot Studio` |
| HTTP request nodes | `HTTP` (endpoint filtering supported) |
| Skills | `Skills with Copilot Studio` |
| Teams/M365 channel | `Microsoft Teams + M365 Channel in Copilot Studio` |
| Direct Line (web/mobile) | `Direct Line channels in Copilot Studio` |
| Facebook / WhatsApp / SharePoint / Omnichannel channels | corresponding per‑channel connectors |
| Event triggers / automated eval | `Microsoft Copilot Studio` |
| Connectors as tools | "Many prebuilt and custom connectors" |
| App Insights wiring | `Application Insights in Copilot Studio` |

### Maker vs admin separation

- **Maker audit logs** flow into Purview — "Admins have full visibility into
  maker audit logs in Microsoft Purview."
- **Agent runtime protection status** is visible to makers on the Agents page;
  **Maker security warning** fires at publish time when a maker deviates from
  default security settings.
- **Disable agent publishing** is a tenant‑level kill switch for
  generative‑AI‑based agents.
- **Data movement across geographic locations** can be disabled for generative
  AI features outside the US.
- Agents created in Copilot Studio can be automatically issued an **Entra
  agent identity** via a per‑environment toggle (`Automatically create Entra
  agent identities for Copilot Studio agents (preview)`). The user who created
  the agent is recorded as its **sponsor**.

### Agent lifecycle (publish, approve, monitor)

1. **Author** in an environment governed by a data policy.
2. **Publish** — DLP runs at publish time; publish is blocked with a
   downloadable per‑violation error sheet if any connector/channel/trigger is
   not permitted.
3. **Monitor** — Sentinel integration and Purview Audit (UAL) surface runtime
   behavior. The CoE Starter Kit dashboard enumerates all agents and
   environments.

> Status: DLP for Copilot Studio is **GA**; automatic Entra Agent ID wiring is
> **Preview**; MCP/advanced connector policies are evolving.

---

## Security Copilot

Security Copilot is useful as a case study because it is both an AI product and
an administrative tool, so Microsoft has had to solve "who audits the auditor".
([Understand authentication in Security Copilot](https://learn.microsoft.com/en-us/copilot/security/authentication)).

### Its own RBAC layer (explicitly not Entra)

Security Copilot defines **exactly two** platform roles:

- **Security Copilot owner**
- **Security Copilot contributor**

"Security Copilot RBAC roles are **not** Microsoft Entra roles. Security Copilot
roles are defined and managed within Copilot and only grant access to Security
Copilot features." A safety rail is baked in: "Security Copilot enforces
retention of two owners at all times. These two owners cannot be removed."

Several Entra and Purview roles auto‑inherit **Copilot owner** to guarantee
that property (Billing Administrator, Entra Compliance Administrator, Global
Administrator, Intune Administrator, Security Administrator; Purview Compliance
Administrator / Data Governance Administrator / Organization Management).

### Layered plugin permissions

"After you're authenticated to the platform, your Microsoft Entra and Azure
Role Based Access Control (RBAC) determines what plugins are available in
prompts." Security Copilot does not grant access beyond what the caller has —
"Security Copilot doesn't go beyond the access you have, aligning with
Microsoft's Security and privacy RAI principle." Each plugin (Sentinel, Intune,
Defender XDR, Entra, Purview, …) carries its own RBAC requirement, evaluated
**per turn**.

Plugin management itself is gated on the Security Copilot role:

| Capability | Owner | Contributor |
| --- | --- | --- |
| Manage personal custom plugins | Yes | Default No |
| Allow contributors to manage personal custom plugins | Yes | No |
| Allow contributors to publish custom plugins for tenant | Yes | No |
| Change availability of pre‑installed plugins for tenant | Yes | No |
| Manage upload file usage | Yes | No |
| Update data sharing / feedback options | Yes | No |
| Capacity management | Yes | No |

### Auditing of the auditor

"Security Copilot today provides access to audit logs through Microsoft Purview
Unified Audit Log (UAL), Microsoft Purview Data Security Posture Management
(DSPM) for AI, and the Office Management API." The **UAL** captures admin events
and activity metadata; **DSPM for AI** captures prompt/response pairs. Shared
sessions are read‑only, per‑tenant, and do **not** re‑evaluate plugin access at
view time — a subtle trust delegation we should note.

---

## Microsoft's normative framing

### Zero Trust applied to agents

Microsoft's March 2026 announcement
([Announcing Zero Trust for AI](https://www.microsoft.com/en-us/security/blog/2026/03/19/new-tools-and-guidance-announcing-zero-trust-for-ai/))
rebuilds the three pillars for AI:

1. **Verify explicitly** — "Continuously evaluate the identity and behavior of
   AI agents, workloads, and users." (Note: "and behavior" — static identity
   isn't enough; agent risk scoring in ID Protection is the behavioral signal.)
2. **Apply least privilege** — "Restrict access to models, prompts, plugins,
   and data sources to only what's needed." (Four axes, not two.)
3. **Assume breach** — "Design AI systems to be resilient to prompt injection,
   data poisoning, and lateral movement."

What changes vs humans, in plain terms:

- Identity is **dynamic and ephemeral** — blueprints are the stable unit, not
  identities.
- The **token `actor` claim** is now first‑class; authorization has to look at
  both user and acting agent.
- **Tool calls are the unit of observation** (Defender's runtime model), not
  API requests. Each invocation is treated as high‑risk.
- **Trust boundaries shift**: overprivileged or manipulated agents are framed
  as "double agents, working against the very outcomes they were built to
  support."
- **Data lineage** extends through prompts/responses/grounded documents;
  oversharing risk is an AI‑era problem, not a traditional DLP problem.

The **Zero Trust Workshop AI Pillar** (GA) covers 700 controls across 33
functional swim lanes. A formal **Zero Trust Assessment for AI** is in
development and announced for **summer 2026**. Five "patterns and practices"
are published: AI threat modeling, AI observability, securing agentic systems,
safety engineering principles, and defense‑in‑depth against indirect prompt
injection.

### Responsible AI Standard (v2)

The Responsible AI Standard v2 is Microsoft's internal governance
contract — every Microsoft AI system is expected to meet it
([RAI Standard v2 — General Requirements PDF](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Microsoft-Responsible-AI-Standard-General-Requirements.pdf)).
Relevant for us:

- **Accountability / Impact Assessments** — designated responsible individuals,
  documented ownership, ongoing monitoring.
- **Transparency Notes** — a public artifact per AI system describing intended
  uses, limitations, and evaluation.
- **System intelligibility for decision making** — stakeholders must be able to
  interpret system responses.
- **Lineage logging** — "who is publishing models, why changes were made, and
  when models were deployed or used in production."
- **Fairness, reliability & safety, privacy & security, inclusiveness** —
  operationalized as measurable requirements rather than principles.

### Reference architectures

- **Cloud Adoption Framework** is explicit that "you don't need a separate AI
  landing zone. AI is just another workload or service that can be deployed,
  governed, and secured within one or more application landing zone
  subscriptions within the existing Azure landing zone architecture"
  ([Azure landing zone FAQ](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/enterprise-scale/faq)).
  This is a deliberate choice: **governance is additive to existing structures,
  not a new parallel plane**. That posture aligns well with a `mcp_pro_governance`
  module that extends Odoo rather than standing up a new silo.
- **Zero Trust reference architecture for AI** (released March 2026) is the
  companion diagram showing where policy/verification/monitoring/governance
  controls slot into the AI lifecycle.
- **Agent Governance Toolkit** on Microsoft TechCommunity provides an open
  architecture deep‑dive on policy engines, trust, and SRE for AI agents —
  useful reading for the policy‑engine shape.

---

## Primitives Microsoft makes explicit that Odoo lacks today

Candidates for direct porting (or reinterpretation) in `mcp_pro_governance`.
Odoo's `res.users`, `res.groups`, `ir.rule`, and `res.partner` cover humans and
companies, and `ir.cron`/`base.automation` cover automation, but none of the
following exist as first‑class primitives:

- **Agent blueprint** as a distinct object from agent instance — name,
  publisher, inheritable Graph/API permissions, inheritable DLP scope,
  inheritable CA policy.
- **Credentials on the blueprint, not the instance** — so fleet‑wide rotation
  is one operation; agent instances never hold secrets at rest.
- **Agent identity** as a non‑user, non‑service‑principal actor, queryable in
  logs with a dedicated type filter.
- **Agent user companion** — optional 1:1 `res.users` for UI surfaces that
  expect a user, with an explicit "this is an agent" decoration.
- **Sponsor attribute**, mandatory, separate from *creator*, auto‑transferable
  to the sponsor's manager on offboarding.
- **Owner vs sponsor vs creator** as three distinct roles on the same object.
- **Custom security attributes** on the agent — attribute‑set / attribute /
  multi‑valued predefined values — usable for downstream policy targeting
  (approval workflow state, department, data‑class scope).
- **Session‑scoped token with audience + action scopes**, where the `actor`
  claim is an agent and the `sub` claim is a user, so audit can tell
  human‑via‑agent from agent‑autonomous.
- **Agent risk score** as a first‑class signal an access/conditional policy
  can read (low/medium/high), with a documented contract for what events raise
  each level.
- **Policy primitives as data objects, not code**:
  - **Data policy** with environment scope, connector classification
    (business/non‑business/blocked), real‑time publish‑time enforcement, and
    a downloadable per‑violation report.
  - **Conditional access policy** with `assignments`, `target resources`,
    `conditions.agent_risk`, `access_controls`, and `state ∈ {on, off, report_only}`.
  - **Sensitivity label propagation** that mirrors grounding‑source labels
    onto responses, including the "highest label wins" rule.
- **Two‑owner minimum invariant** on any administrative object (Security
  Copilot's pattern) — prevents accidental deletion of the last owner.
- **Access packages for agents** — Microsoft's entitlement model with expiry,
  sponsor‑requested extensions, and automatic expiration as the fallback path.
- **Publish gate that blocks and reports** — agents can't go live while any
  connector/channel/trigger/skill is non‑compliant; violation report is
  exportable per agent.
- **Audit schema with `AgentId`, `AgentName`, `AgentVersion`, `AppIdentity`,
  `AppHost`, `Operation`, `Messages[].isPrompt`, `Messages[].JailbreakDetected`,
  `AccessedResources[].XPIADetected`, `AccessedResources[].SensitivityLabelId`,
  `AccessedResources[].PolicyDetails`, `ModelTransparencyDetails`** — the
  minimum viable record type for agentic AI auditability.
- **DSPM‑for‑AI‑style inventory**: a single "AI apps and agents" dashboard
  that joins identity, activity, data touched, and policy coverage per agent.
- **Oversharing risk assessment** — a scheduled job that scans high‑activity
  repositories (in Odoo terms: document workspaces, attachments by record,
  knowledge articles) for external‑share and sensitivity‑label coverage before
  letting an agent ground on them.
- **Runtime "every tool call is a high‑risk event"** — evaluation hook
  pattern that can allow/deny/warn each tool invocation with reason codes,
  independent of the agent's own orchestration.
- **A published Transparency Note per agent** — a structured record covering
  intended use, limitations, evaluations, and human fallback, versioned
  alongside the agent.
- **Human fallback / pause switch** — `disable_agent` as a first‑class
  sponsor/owner action surfaced in a self‑service portal (Microsoft's "My
  Account" equivalent).
- **Data policy exemptions are explicitly not supported** — treat this as a
  lesson. Once enforcement ships, it must apply uniformly; per‑agent DLP
  exemptions lead to silent drift.

## Open questions for synthesis

1. **Do we actually model blueprint + identity separately, or collapse them?**
   Microsoft's decomposition is the right shape at Entra scale (1000s of ephemeral
   agents per day). In an ERP tenant the cardinality is much lower. Collapsing to
   one `mcp.agent` with a `template_id` self‑reference might be sufficient and
   far cheaper — but we lose Microsoft's "one CA policy covers the fleet"
   property. Recommend resolving this early with a cardinality estimate.
2. **Where does the token `actor` claim live in Odoo?** Odoo's RPC layer doesn't
   carry a second subject. If we want the
   "human‑via‑agent vs human‑direct vs agent‑autonomous" distinction to appear in
   `mail.message` and audit, we need a server‑level context primitive
   (thread‑local, like `request.uid`) — e.g. `env.agent_uid`. This is a design
   decision that ripples into every ORM write.
3. **How much of Purview do we reimplement vs wrap?** Audit, DLP,
   sensitivity labels, communication compliance, eDiscovery, lifecycle
   retention — all exist as Odoo‑external concerns. Do we define an *interop
   contract* (e.g. stream events to an external SIEM/Purview) instead of
   re‑implementing DSPM? Recommendation: the audit schema above is small enough
   that Odoo should *emit it* natively and leave storage/analysis external.
4. **Sponsor transfer on offboarding.** Microsoft auto‑transfers sponsorship to
   the sponsor's manager via Lifecycle Workflows. Odoo has `hr.employee.parent_id`
   but no generic "manager" concept on `res.users`. Do we require the HR module,
   or define our own reassignment policy?
5. **What is the Odoo‑native analogue to "connector data groups"?** Copilot
   Studio's business/non‑business/blocked trichotomy is enforced per environment
   at publish time. In Odoo, the equivalent of "environment" is fuzzy —
   database, company, or project? And "connector" ≈ what: an outgoing webhook,
   an `ir.actions.server`, an MCP tool? We need a crisp mapping before policies
   can be written against it.
6. **Agent risk score — where does it come from?** In Entra it's an Identity
   Protection product signal. We would have to either (a) accept an external
   signal, (b) compute one from local heuristics (recent jailbreak detections,
   rate of tool calls, rate of DLP hits), or (c) expose a hook and leave the
   scoring to third parties. Option (b) is the minimum useful default.
7. **Two‑owner invariant — apply globally?** Worth applying not just to the
   module's admin object, but to every individual agent, so an orphaned agent
   can't be deleted before its owner list is rebuilt.
8. **Preview‑vs‑GA stability.** As of 2026‑04‑24, the primitives in the memo
   that are **GA**: Purview DLP for M365 Copilot, DSPM for AI (classic), Copilot
   Studio DLP enforcement, MDA generative‑AI discovery/governance, Security
   Copilot RBAC, Zero Trust AI Workshop. **Preview**: Entra Agent ID (all four
   object types), Conditional Access for agents, Identity Protection for agents,
   ID Governance for agents, automatic Agent ID for Copilot Studio, Defender
   XDR runtime agent protection, new unified DSPM, Purview for agents (GA due
   late May 2026). We should port GA primitives as stable schema and keep the
   Preview ones abstract enough to track without being locked in.
9. **License and distribution.** All of the above sits behind Microsoft 365
   Copilot + Frontier program licensing. For an **open‑source** Odoo module, we
   cannot assume any of these backing services; the module must define its own
   primitives and optionally *integrate* with Microsoft (or any other) provider.
   The question for synthesis: is `mcp_pro_governance` primarily an integration
   layer for customers who *do* run Entra + Purview, a standalone reimagining,
   or both with a clean seam?
10. **Normative alignment.** Do we commit to an explicit RAI‑v2‑style
    "Transparency Note per agent" as mandatory metadata (with validation on
    publish)? This is cheap to port and gives `mcp_pro_governance` a defensible
    posture, but it is philosophically stronger than anything currently in
    Odoo core.
