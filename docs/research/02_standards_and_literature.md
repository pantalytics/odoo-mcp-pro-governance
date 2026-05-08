# 02 — Standards and Literature: Normative Landscape for `mcp_pro_governance`

**Author:** rutger@pantalytics.com
**Date:** 2026-04-24
**Scope:** Map the standards, regulations, security frameworks, and authoritative literature that the `mcp_pro_governance` Odoo module must engage with, and identify which clauses are *normatively binding* (force a design choice) versus which are *advisory* (shape best practice).

The module sits at an unusual intersection: it is an ERP-resident control plane for both data and AI governance, explicitly intended to host Model Context Protocol (MCP) tool surfaces and agentic workflows against live business records. That means it is simultaneously (i) a deployer-side AI governance system under the EU AI Act, (ii) a data-processing layer under GDPR, (iii) an auditable business application under ISO 27001/42001, and (iv) an MCP host that must defend against the OWASP LLM and Agentic AI threat classes. Each of those framings imposes overlapping but distinct requirements.

---

## 1. NIST AI Risk Management Framework (AI RMF 1.0) and the Generative AI Profile (NIST AI 600-1)

The AI RMF is the dominant US-origin governance framework and, although voluntary, is explicitly cross-walked by CSA's AI Controls Matrix, ISO 42001, and several EU AI Act implementing documents. It is therefore effectively baseline.

### 1.1 The four functions

The AI RMF Core defines four functions that, together, constitute a lifecycle approach. Each is decomposed into categories (e.g. `GV-1`) and subcategories (e.g. `GV-1.1`) which are the actual actionable outcomes. The functions, taken from the [AI RMF 1.0 Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/):

- **GOVERN** — "cultivates a culture of risk management" and "is a cross-cutting function that is infused throughout AI risk management and enables the other functions." This is the one that lands directly on an ERP governance module: it requires policies, accountability structures, legal/regulatory tracking, third-party risk management, and training.
- **MAP** — "establishes the context to frame risks related to an AI system." Requires cataloguing intended purpose, affected populations, component provenance, and context-specific risk.
- **MEASURE** — "employs quantitative, qualitative, or mixed-method tools, techniques, and methodologies to analyze, assess, benchmark, and monitor AI risk and related impacts." This is where test sets, metrics, TEVV artefacts, security/resilience evaluation, and privacy risk measurement live.
- **MANAGE** — "entails allocating risk resources to mapped and measured risks on a regular basis and as defined by the GOVERN function." Covers prioritisation, residual-risk documentation, incident response, and post-deployment monitoring.

### 1.2 Subcategories that force ERP primitives

These AI RMF subcategories have direct, concrete analogues in an ERP:

| AI RMF Subcategory | Requirement (paraphrased) | ERP primitive in `mcp_pro_governance` |
|---|---|---|
| `GV-1.1` | Legal and regulatory requirements involving AI are understood, managed, and documented | Regulatory register model (`governance.regulation`) with versioned citations |
| `GV-1.5` | Ongoing monitoring and periodic review with defined organisational roles | Scheduled review cron + `mail.activity` for accountable user |
| `GV-2.1` | Roles, responsibilities, and communication lines documented | Role model tied to `res.users` + `res.groups`, RACI field |
| `GV-6.1` | Policies addressing risks from third parties and IP | Vendor AI register (`governance.ai_vendor`) with clause tracking |
| `GV-6.2` | Contingency processes for high-risk third-party failures | Fallback-policy fields on each MCP tool binding |
| `MAP-1.1` | Intended purposes, deployment settings, assumptions, limitations documented | System card record per AI system |
| `MAP-4.1` | Approaches for mapping AI technology and legal risks of components are in place | Component SBOM/AIBOM link on the system card |
| `MEASURE-2.1` | Test sets, metrics, and TEVV tools documented | Evaluation-run records attached to each model version |
| `MEASURE-2.7` | Security and resilience evaluated and documented | Red-team and pen-test log on system card |
| `MEASURE-2.10` | Privacy risk examined and documented | DPIA artefact link |
| `MANAGE-1.4` | Residual risks documented | Residual-risk field with sign-off by accountable role |
| `MANAGE-4.1` | Post-deployment monitoring, incident response, recovery, change management | Immutable audit log + incident model (`governance.incident`) |
| `MANAGE-4.3` | Incident communication and tracking | Notification routing + stakeholder register |

### 1.3 Generative AI Profile (NIST AI 600-1)

[NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) identifies twelve risks "unique to or exacerbated by" generative AI. These directly inform what the module's risk taxonomy vocabulary must support:

1. **CBRN Information or Capabilities** — generative AI may "lower barriers" to chemical/biological/radiological/nuclear weapon-relevant information. For an ERP module this largely surfaces as *content filtering policy* and *tool-exposure restriction*.
2. **Confabulation** — "the production of confidently stated but erroneous or false content." Drives the need for *provenance labelling* on AI-generated fields and for *human-review workflows* before records are committed.
3. **Dangerous, Violent, or Hateful Content** — drives content-policy on both inputs and outputs.
4. **Data Privacy** — overlap with GDPR; drives redaction/DLP and training-data governance.
5. **Environmental Impacts** — largely reporting; drives optional compute-cost ledger.
6. **Harmful Bias and Homogenization** — drives fairness testing metadata fields.
7. **Human-AI Configuration** — drives mandatory transparency artefacts (this is AI; here is what it cannot do; here is how to escalate).
8. **Information Integrity** — drives content-provenance (C2PA-style) and watermarking metadata support.
9. **Information Security** — drives secure-by-default tool binding, secret management, and incident response.
10. **Intellectual Property** — drives training-data licence register.
11. **Obscene, Degrading, or Abusive Content** — content policy.
12. **Value Chain and Component Integration** — drives AIBOM/SBOM tracking for every plugged-in model, embedding store, and tool.

### 1.4 Normative vs advisory

The AI RMF is explicitly voluntary ("this Framework is voluntary"), so *on its own* it does not force anything. But because CSA AICM, ISO 42001 Annex A, and the EU AI Act implementing acts all reference it, the practical effect is that **`GV-1`, `GV-6`, `MAP-4`, `MEASURE-2.7`, `MEASURE-2.10`, and `MANAGE-4.1` are de-facto mandatory** for any defensible deployment.

---

## 2. ISO/IEC 42001:2023 — AI Management System

[ISO/IEC 42001:2023](https://www.iso.org/standard/42001) is the first certifiable AI management system standard. It follows the harmonised ISO management-system structure (Annex SL / High-Level Structure), meaning it is explicitly designed to be integrated with ISO 9001, ISO 27001, and ISO 27701.

### 2.1 Structure

Clauses 4–10 cover the standard PDCA cycle: **Context (4), Leadership (5), Planning (6), Support (7), Operation (8), Performance evaluation (9), Improvement (10)**. Certification is against these clauses; Annex A is the normative control list that Clause 6.1.3 "Treatment of AI risks" points at. A Statement of Applicability (SoA) is required for each Annex A control, matching ISO 27001 practice.

### 2.2 Annex A controls most relevant to an ERP governance module

| Control area | Focus | ERP module implication |
|---|---|---|
| **A.2 Policies related to AI** | Top-level AI policy; alignment with org policies | Policy document model with approval workflow |
| **A.3 Internal organization** | Roles, responsibilities, reporting | Role catalogue + RACI fields |
| **A.4 Resources for AI systems** | Data, tooling, computing, human resources | Resource inventory model |
| **A.5 Assessing impacts of AI systems** | AI system impact assessment (AIIA) | AIIA template (`governance.aiia`) with sign-off |
| **A.6 AI system life cycle** | Requirements → design → verification → deployment → operation → retirement | Stage-gated workflow on each AI system record |
| **A.7 Data for AI systems** | Data quality, provenance, preparation | Training-data register with provenance fields |
| **A.8 Information for interested parties of AI systems** | Transparency documentation for users, subjects, regulators | System card publication endpoint |
| **A.9 Use of AI systems** | Responsible use; intended-purpose guardrails | Tool-binding allow-lists, usage logs |
| **A.10 Third-party and customer relationships** | Allocate responsibility across the value chain | Vendor AI register with contract clauses |

(Note: some secondary sources use different A.5–A.10 numbering depending on which draft they read; the above reflects the published ISO/IEC 42001:2023 structure. Consult [ISO/IEC 42001:2023 preview](https://cdn.standards.iteh.ai/samples/81230/4c1911ebc9a641fcb6ee21aa09c28ad3/ISO-IEC-42001-2023.pdf) for the authoritative list.)

### 2.3 Relationship to ISO/IEC 27001

ISO 42001 explicitly builds on, and refers to, ISO/IEC 27001 and ISO/IEC 27701. AI risks that are "information security" in character still fall under 27001's Annex A (updated 2022), and AI systems that process personal data remain governed by 27701. The practical consequence: **an ISO 42001-compliant ERP module can re-use 27001 controls for access management, cryptography, logging, and incident response, and only needs AI-specific additions for impact assessment, training-data governance, and transparency documentation.**

### 2.4 Normative vs advisory

ISO 42001 clauses 4–10 are **mandatory for certification**. Annex A is normative in the sense that controls can only be excluded with justification in the SoA. For a governance module targeting ISO 42001 readiness, *all* of A.2, A.3, A.5, A.6, A.7, A.8, A.9, A.10 should have at least scaffolded support.

---

## 3. EU AI Act — Regulation (EU) 2024/1689

The [AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng) entered into force on **1 August 2024** and is the binding regulation in the EU. It is directly applicable — no national transposition is required for most provisions.

### 3.1 Risk tiers

| Tier | What it means | Primary obligation |
|---|---|---|
| **Prohibited** (Art. 5) | Social scoring, manipulative techniques, real-time RBI with narrow exceptions, etc. | Cannot be placed on the market or used |
| **High-risk** (Arts. 6–7, Annex III) | Employment, education, critical infrastructure, law enforcement, biometrics, essential services, etc. | Conformity assessment + Chapter III, Section 2 obligations (Arts. 9–15) for providers; Art. 26 for deployers |
| **Limited / transparency** (Art. 50) | Chatbots, emotion-recognition, biometric categorisation, deepfakes, GenAI text on matters of public interest | Transparency disclosures |
| **Minimal** | Everything else | Voluntary codes of conduct |
| **GPAI** (Arts. 51–55) | General-purpose AI models (incl. foundation models) | Art. 53 documentation, Art. 55 systemic-risk duties |

### 3.2 Deployer vs provider — who does what

This is load-bearing for an Odoo module, because an Odoo customer using `mcp_pro_governance` to orchestrate a third-party LLM is almost always a **deployer**, not a provider, of that LLM. But they may become a *provider* if they substantially modify the system, put their own name on it, or change its intended purpose (Art. 25).

- **Providers** carry most of Chapter III, Section 2 (Arts. 9–15): risk management, data governance, technical documentation, record-keeping, transparency, human oversight, accuracy/robustness/cybersecurity, QMS (Art. 17), registration (Art. 49).
- **Deployers** carry Art. 26 (and Art. 27 FRIA where applicable, plus transparency toward workers and natural persons).

### 3.3 Key articles and what they force

**Art. 9 — Risk management system.** "A risk management system shall be established, implemented, documented and maintained in relation to high-risk AI systems" and "shall be understood as a continuous iterative process planned and run throughout the entire lifecycle of a high-risk AI system, requiring regular systematic review and updating." Full text at [Art. 9](https://artificialintelligenceact.eu/article/9/). → forces a **lifecycle-linked risk register** primitive; not a static register.

**Art. 10 — Data and data governance.** "Training, validation and testing data sets shall be subject to data governance and management practices appropriate for the intended purpose" and must be "relevant, sufficiently representative, and to the best extent possible, free of errors and complete." → forces **training-data register with lineage, bias-check, and completeness flags**. See [Art. 10](https://artificialintelligenceact.eu/article/10/).

**Art. 12 — Record-keeping.** "High-risk AI systems shall technically allow for the automatic recording of events (logs) over the lifetime of the system." Logs must support identifying risk situations, post-market monitoring, and monitoring of operation. Per Art. 26(6), **deployers must retain logs for at least six months** unless other Union or national law (particularly data protection) applies. → forces an **immutable, append-only audit log with minimum 6-month retention** and, for financial services, whatever DORA/sectoral law imposes (often 5–7 years). See [Art. 12](https://artificialintelligenceact.eu/article/12/).

**Art. 13 — Transparency.** Requires "instructions for use" to accompany the system and to contain characteristics, capabilities, limitations, human oversight measures, expected lifetime, and maintenance. → forces an **instructions-for-use artefact generator** tied to each high-risk AI system record.

**Art. 14 — Human oversight.** "High-risk AI systems shall be designed and developed in such a way…that they can be effectively overseen by natural persons during the period in which they are in use." Art. 14(4) lists oversight capabilities the system must enable: understand capacities/limitations, remain aware of automation bias, correctly interpret output, decide not to use, intervene and stop ("stop button"). → forces **per-tool kill-switch, per-decision override, and automation-bias warnings** in the UI.

**Art. 15 — Accuracy, robustness, cybersecurity.** Must be designed "in such a way that they achieve an appropriate level of accuracy, robustness, and cybersecurity." Must resist "unauthorised third parties" altering use or performance, and address "AI-specific vulnerabilities" including "data poisoning," "model poisoning," "model evasion," "confidentiality attacks," and "model flaws." → maps directly onto OWASP LLM Top 10 + MITRE ATLAS controls.

**Art. 26 — Deployer obligations** (full paragraphs from [Art. 26](https://artificialintelligenceact.eu/article/26/)):
- (1) Use in accordance with instructions for use.
- (2) Assign human oversight to natural persons with competence, training, authority, and support.
- (4) Ensure input data is relevant and sufficiently representative "to the extent the deployer exercises control over the input data."
- (5) Monitor operation; inform provider and market surveillance authority; suspend use if risk identified.
- (6) **Keep automatically generated logs for at least six months** (longer if required by other law).
- (7) Inform workers before using high-risk AI that affects them.
- (8) Register use in EU database for public-body deployers.
- (9) Use Art. 13 information to fulfil **GDPR Art. 35 DPIA obligations** — bridges GDPR and AI Act.
- (11) Inform natural persons subject to decisions made with the system.
- (12) Cooperate with competent authorities.

→ Art. 26 is the single most load-bearing article for an ERP-side governance module. It forces: an instructions-for-use registry, a human-oversight assignment model, an input-data monitoring gate, a log retention regime, a worker-notification log, and a DPIA link.

**Art. 50 — Transparency for certain AI systems.** Providers of interactive AI must make users aware they are interacting with AI; providers of generative systems must mark outputs as AI-generated in a machine-readable manner; deployers of emotion-recognition or biometric-categorisation systems must inform affected persons; deployers of deepfake-generating systems must disclose artificial content. See [Art. 50](https://artificialintelligenceact.eu/article/50/). → forces a **provenance/watermark metadata attachment** capability, and a **disclosure banner** primitive.

**Arts. 53–55 — GPAI.**
- **Art. 53** — All GPAI providers: maintain technical documentation, provide downstream documentation, have a copyright-policy, publish a public summary of training content.
- **Art. 55** — GPAI with systemic risk (≥ 10^25 FLOPs training compute threshold): model evaluation, adversarial testing, systemic-risk assessment, serious-incident reporting, adequate cybersecurity.
- **Code of Practice.** The final [GPAI Code of Practice](https://digital-strategy.ec.europa.eu/en/policies/ai-code-practice) was published in July 2025 and, per the European Commission, compliance with the Code is treated as presumption of conformity with Arts. 53/55 for signatories. A separate **Code of Practice on Transparency of AI-Generated Content** (first draft Dec 2025; final expected June 2026) operationalises Art. 50.

### 3.4 Timeline — what is in force as of 2026-04-24

| Date | What applies |
|---|---|
| 1 Aug 2024 | Entry into force |
| **2 Feb 2025** | Chapter I (general provisions) + Chapter II (prohibited practices, Art. 5) + AI literacy (Art. 4) |
| **2 Aug 2025** | Chapter III Section 4 (notifying authorities), Chapter V (GPAI), Chapter VII (governance), Chapter XII (penalties, except Art. 101) |
| **2 Aug 2026** | Remainder — crucially, Annex III high-risk obligations, Art. 26 deployer obligations, and Art. 50 transparency. **This is the hard deadline we are approximately four months away from as of this memo.** |
| 2 Aug 2027 | High-risk AI embedded in products already regulated under Annex I harmonisation legislation |

**Practical consequence for the module:** Art. 26 deployer obligations and Art. 50 transparency are **not yet in force today** but will be **within 100 days**. The module must ship those features before 2026-08-02 to be usable by any EU deployer of an Annex III system. See the [EU AI Act Implementation Timeline](https://artificialintelligenceact.eu/implementation-timeline/).

---

## 4. OWASP — LLM Top 10 (2025) and Agentic AI Threats and Mitigations

The OWASP GenAI Security Project publishes two overlapping documents that are directly actionable for any MCP-hosting module.

### 4.1 LLM Top 10 (2025)

[OWASP Top 10 for LLM Applications v2025](https://genai.owasp.org/llm-top-10/) (November 2024, revised 2025). Ten categories; I highlight the five that materially change the module's design:

| ID | Name | Direct implication for `mcp_pro_governance` |
|---|---|---|
| **LLM01** | [Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | All data read by the agent from ERP records is *untrusted input*. Forces input/output mediation, segregation of system vs user content, semantic filtering, and out-of-band confirmation for sensitive actions. |
| **LLM02** | Sensitive Information Disclosure (jumped from #6 → #2 in 2025) | Forces row-level access enforcement at the MCP tool layer, PII scrubbing policies, and output DLP. |
| **LLM03** | Supply Chain | AIBOM/SBOM tracking on every model, embedding, plugin, MCP tool. |
| **LLM04** | Data and Model Poisoning | Training/fine-tune data provenance fields; embedding store integrity checks. |
| **LLM05** | Improper Output Handling | Validate/escape model output before writing back to ERP records. |
| **LLM06** | Excessive Agency (Functionality / Permissions / Autonomy) | **This is the core of the module.** Forces least-privilege tool bindings, per-user/per-session scope, explicit approval gates for write actions, and cap on autonomy (e.g. no chained writes without human sign-off). |
| **LLM07** | System Prompt Leakage (new in 2025) | System prompts must not carry secrets; secrets live in the credential vault, referenced by handle. |
| **LLM08** | Vector and Embedding Weaknesses (new in 2025) | Embedding stores need access control, integrity verification, and re-embedding after source deletion (right-to-be-forgotten). |
| **LLM09** | Misinformation | Provenance labelling on AI-written fields. |
| **LLM10** | Unbounded Consumption | Rate limits, cost caps, concurrency caps per agent and per tool. |

**LLM01 is load-bearing.** OWASP's recommended mitigations — "constrain behavior via detailed system prompts," "validate outputs," "filter inputs/outputs," "enforce least privilege," "require human approval for high-risk operations," "segregate external content with clear labeling of untrusted sources," "conduct adversarial testing" — map one-to-one onto module features.

### 4.2 Agentic AI — Threats and Mitigations and the OWASP Agentic AI Top 10 (2026)

The February 2025 [Agentic AI Threats and Mitigations guide](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/) enumerates 15 threat classes (T1–T15) and was followed in December 2025 by the [OWASP Top 10 for Agentic Applications (ASI01–ASI10)](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/). The mapping:

| OWASP Agentic Top 10 (ASI) | Representative threat(s) in T1–T15 | Module primitive |
|---|---|---|
| **ASI01 Agent Goal Hijack** | T1 Memory Poisoning; goal manipulation | Signed goal-statement; immutable task envelope |
| **ASI02 Tool Misuse & Exploitation** | T2 Tool Misuse | Tool allow-list per role; parameter schema validation; pre-execution policy engine |
| **ASI03 Identity & Privilege Abuse** | Identity spoofing; privilege compromise | Delegated-identity model distinct from `res.users`; scoped tokens per session |
| **ASI04 Supply Chain Vulnerabilities** | Compromised MCP servers, plugins | MCP server registry with pinned versions and integrity hashes |
| **ASI05 Unexpected Code Execution** | RCE via generated code | Sandboxing; no `exec` on model output without a reviewed template |
| **ASI06 Memory & Context Poisoning** | T1 Memory Poisoning | Per-tenant memory isolation; memory quarantine on anomaly |
| **ASI07 Insecure Inter-Agent Communication** | Agent-to-agent spoofing | Mutual authentication (mTLS or signed envelopes) between agents |
| **ASI08 Cascading Failures** | T5 Cascading Hallucination | Hallucination flag propagation; circuit breakers |
| **ASI09 Human-Agent Trust Exploitation** | T15 Human Manipulation | UI affordances that state "AI suggestion, unverified"; confirmation for high-stakes |
| **ASI10 Rogue Agents** | Goal drift; unauthorised agent creation | Agent registry with lifecycle state; anomaly-detection on action distributions |

OWASP's headline mitigations for agentic systems: **strict access control with granular permissions; monitoring and behavioural profiling to detect anomalies; validation of agent inputs and outputs; secure communication channels.** These are baseline.

---

## 5. Cloud Security Alliance — AI Controls Matrix (AICM)

The [CSA AI Controls Matrix v1.0](https://cloudsecurityalliance.org/artifacts/ai-controls-matrix) was released in July 2025 as a successor/complement to CCM for AI workloads. Its distinguishing feature is that it is **cross-walked** to ISO 42001, ISO 27001, NIST AI RMF, and BSI AIC4 — so it functions as an integration layer.

### 5.1 Structure

AICM v1.0 contains **243 control objectives across 18 security domains**. Domains include: Identity & Access Management, Model Security, Data Security, Threat and Vulnerability Management, Incident Response, Supply Chain, Business Continuity, Governance Risk and Compliance, Logging and Monitoring, Privacy, Human Resources, Interoperability & Portability, Application and Interface Security, Change and Configuration Management, Cryptography, Infrastructure Security, Audit Assurance and Compliance, and Bias & Fairness.

### 5.2 Controls that translate to ERP primitives

- **IAM domain** — per-agent identities, credential rotation, scoped tokens. Maps to `governance.agent_identity` with Odoo's `res.users` chain-of-custody.
- **Logging & Monitoring** — immutable logs, tamper evidence, retention. Maps to an append-only `governance.audit_event` model with optional hash chain.
- **Model Security** — model integrity verification, version pinning, provenance. Maps to `governance.model_binding` with hash + SBOM link.
- **Data Security** — classification, DLP, provenance. Maps to data-classification tags on `ir.model` / `ir.model.fields`.
- **Supply Chain** — vendor assessment, AIBOM. Maps to `governance.ai_vendor` and `governance.aibom`.
- **Bias & Fairness** — evaluation artefacts. Maps to `governance.evaluation` with bias-metric fields.

AICM also ships a **CAIQ for AI** (Consensus Assessment Initiative Questionnaire) — a self-assessment or vendor-assessment template. An ERP module should export a CAIQ-compatible report.

### 5.3 Normative status

AICM is non-mandatory but increasingly requested by enterprise procurement, and signing a CSA STAR attestation is becoming a contract precondition for cloud AI vendors. It is advisory but **strongly recommended** for market readiness.

---

## 6. MITRE ATLAS

[MITRE ATLAS](https://atlas.mitre.org/) (Adversarial Threat Landscape for AI Systems) is the ATT&CK-for-AI. As of the **v5.4.0 release (February 2026)**, it contains **16 tactics, 84 techniques, 56 sub-techniques, 32 mitigations, and 42 case studies**.

### 6.1 Tactics relevant to ERP-hosted AI

ATLAS tactics mirror ATT&CK: Reconnaissance, Resource Development, Initial Access, ML Model Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Collection, Command and Control, Exfiltration, Impact — plus AI-specific ones such as ML Attack Staging and ML Supply Chain Compromise.

Techniques with the highest salience for ERP-hosted agents:

- **AML.T0051 Prompt Injection** (Initial Access) — direct and indirect variants.
- **AML.T0010 ML Supply Chain Compromise** — poisoned model weights, compromised adapters, tampered embeddings.
- **AML.T0053 LLM Plugin Compromise** — plugin/tool abuse; maps to "Publish Poisoned AI Agent Tool" added in v5.4.0.
- **AML.T0057 LLM Data Leakage** — maps to LLM02 and to GDPR obligations.
- **Escape to Host** (added v5.4.0) — execution escape from sandboxed agent runtime; drives sandboxing requirements.
- **AML.T0048 External Harms** — models' outputs causing downstream damage; maps to Art. 15 AI Act.

### 6.2 How it complements ATT&CK

ATT&CK covers the infrastructure hosting the agent (OS, network, identity). ATLAS covers the AI-specific layer. An ERP module should maintain mappings in both: a single control like "tool-parameter schema validation" mitigates both AML.T0053 (ATLAS) and T1059 Command and Scripting Interpreter (ATT&CK). Publish the cross-walk in the module's security documentation.

### 6.3 Normative status

MITRE ATLAS is advisory, but it is the most widely referenced taxonomy of AI attacks and is used by ENISA, NIST, and many sectoral regulators. Not implementing controls against the high-severity ATLAS techniques would be difficult to defend in a post-incident investigation.

---

## 7. Academic and authoritative references

These are selected because they are peer-reviewed, institutional, or highly cited — not blog posts.

- **Shavit, Y., Agarwal, S., et al. (OpenAI). _Practices for Governing Agentic AI Systems_**, 2023. Seminal industry paper enumerating controls: identifiability, agent task specification, default behaviour constraints, interruptibility, visibility to relevant parties, accountability. [PDF](https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf). Directly motivates the "signed task envelope" and "agent identity register" primitives.
- **Chan, A., et al. _Harms from Increasingly Agentic Algorithmic Systems_**. FAccT 2023, [arXiv:2302.10329](https://arxiv.org/abs/2302.10329). Taxonomy of harms in agentic systems; informs risk register categories.
- **Weidinger, L., et al. _Taxonomy of Risks Posed by Language Models_**. FAccT 2022, DOI [10.1145/3531146.3533088](https://doi.org/10.1145/3531146.3533088). Foundation for NIST AI 600-1's GenAI risk taxonomy.
- **Bommasani, R., et al. _On the Opportunities and Risks of Foundation Models_**. Stanford CRFM, 2021, [arXiv:2108.07258](https://arxiv.org/abs/2108.07258). Canonical reference for foundation-model risk framing.
- **Carnegie Endowment for International Peace — _Governing AI Agents_**, 2024–2025 working papers. Policy-oriented treatment of delegation, liability, and oversight.
- **Stanford HAI _AI Index 2025_**. Empirical baseline on incident counts and governance adoption; useful for risk-calibration.
- **Brookings Institution — _AI governance for the public interest_**, 2024–2025. Public-sector framing of deployer obligations.
- **BIS (Bank for International Settlements) — _Generative AI and the finance function_**, 2024. Central-bank framing relevant if the module is used in regulated financial deployments; pairs with DORA.
- **ENISA _Multilayer Framework for Good Cybersecurity Practices for AI_**, 2023, and _Securing Machine Learning Algorithms_, 2021. Three-layer model: ICT foundation → AI-specific → sectoral. ENISA is the EU cybersecurity agency; its frameworks are non-binding but are referenced by NIS2 implementation guidance. See [ENISA AI publications](https://www.enisa.europa.eu/publications/multilayer-framework-for-good-cybersecurity-practices-for-ai).
- **A Safety and Security Framework for Real-World Agentic Systems**, [arXiv:2511.21990](https://arxiv.org/abs/2511.21990), 2025. Formalises auditability axioms — Integrity, Coverage, Temporal Coherence, Verifiability, Accessibility, Resource Proportionality, Privacy Compatibility, Governance Alignment. Directly motivates hash-linked per-action audit entries.
- **The Agentic Regulator: Risks for AI in Finance**, [arXiv:2512.11933](https://arxiv.org/abs/2512.11933), 2025. Financial-sector treatment of agentic governance; pairs with DORA.
- **Oversight Structures for Agentic AI in Public-Sector Organizations**, [arXiv:2506.04836](https://arxiv.org/abs/2506.04836), 2025. Useful on separation-of-duties patterns.
- **Microsoft AI Red Team — _Taxonomy of failure modes in AI agents_**, 2024. Enumerates agent compromise, workflow manipulation, multi-agent jailbreak; motivates tamper-resistant logging.

Separation-of-duties in AI contexts is an open research area: the widely cited observation is that when an agent can grant itself access to a knowledge system, SoD is structurally violated and must be re-imposed at the ERP layer (see ISACA's 2025 industry piece [The Growing Challenge of Auditing Agentic AI](https://www.isaca.org/resources/news-and-trends/industry-news/2025/the-growing-challenge-of-auditing-agentic-ai)).

---

## 8. Other regulations worth flagging

### 8.1 GDPR

- **Art. 22 — Automated individual decision-making.** A data subject has the right "not to be subject to a decision based solely on automated processing, including profiling, which produces legal effects concerning him or her or similarly significantly affects him or her." Exceptions: contractual necessity, Union/MS law with safeguards, explicit consent. Where exceptions apply, the controller must implement "suitable measures to safeguard the data subject's rights," "at least the right to obtain human intervention," to express a view, and to contest. See [Art. 22 GDPR](https://gdpr-info.eu/art-22-gdpr/). → forces **human-intervention endpoint and contestation workflow** for any automated decision.
- **Art. 30 — Records of processing.** Forces the module to maintain a **processing register** covering every AI processing activity (purpose, categories of data, categories of subjects, retention, cross-border transfers).
- **Art. 35 — DPIA.** Where processing is likely to result in high risk, a DPIA is mandatory. EU AI Act Art. 26(9) explicitly ties this to AI deployment. → DPIA artefact template with EU AI Act section cross-reference.
- **Art. 5 accountability principle, Art. 32 security of processing, Art. 25 data protection by design.** All directly touch embedding stores, log contents, and model training data handling.

### 8.2 NIS2 (Directive (EU) 2022/2555)

Applies to essential and important entities (energy, transport, health, digital infrastructure, finance outside DORA scope, public administration, etc.). Obligations relevant to AI integrations:
- **Art. 21** — cybersecurity risk management measures, explicitly including supply-chain security. AI models and vector stores are part of the supply chain.
- **Art. 23** — incident reporting with 24-hour early warning and 72-hour detailed notification. → module should support **structured incident export** conforming to CSIRT templates.

Deadlines for national transposition passed in October 2024; most member states are now enforcing NIS2. For the Netherlands, the **Cyberbeveiligingswet (Cbw)** is the transposition; it entered into force in phases through 2025.

### 8.3 DORA — Regulation (EU) 2022/2554

Applies to financial entities and their ICT third-party service providers. **Entered full application on 17 January 2025.** Key articles:
- **Art. 5–14** — ICT risk management framework.
- **Art. 17–23** — ICT-related incident reporting.
- **Art. 24–27** — digital operational resilience testing (incl. TLPT for significant entities).
- **Art. 28–44** — third-party risk management (register of information, critical ICT third-party providers). **AI vendors are ICT third parties.**
- **Art. 30** — mandatory contractual clauses with ICT third parties.

For financial deployers of the module, DORA's third-party register overlaps heavily with ISO 42001 A.10 and AI Act Art. 26(5). DORA is **lex specialis** to NIS2 for financial entities.

### 8.4 Member-state-specific notes

- **Netherlands.** The **Autoriteit Persoonsgegevens (AP)** has appointed itself as coordinating supervisor for AI, with a dedicated DCA (Directie Coördinatie Algoritmes). Its algorithm register expectations and *Kader Generatieve AI* (for public sector) shape Dutch public-sector deployments. National AI Act implementing legislation (Uitvoeringswet AI-verordening) is in preparation as of early 2026.
- **Germany.** The BfDI and BSI AIC4 catalogue remain referenced by CSA AICM.
- **France.** CNIL has published sectoral guidance on GenAI training-data lawfulness and transparency.
- **Ireland.** DPC guidance on Art. 22 GDPR is the de-facto standard because many US vendors use Ireland as their EU establishment.

---

## Hard requirements (must-have in the module to be defensible)

These are driven by binding law or by standards whose absence would be indefensible in audit or incident response.

- **Immutable, append-only audit log with hash chain.** Required by EU AI Act Art. 12 and Art. 26(6) (min 6-month retention); extended retention for DORA (effectively 5+ years) and NIS2; supports GDPR Art. 30 and ISO 27001 A.8.15/A.8.16.
- **Per-agent identity register distinct from `res.users`.** Required to enforce attribution in logs (AI RMF `MANAGE-4.1`, OWASP ASI03, academic auditability axioms).
- **Tool allow-list with least-privilege scope per role, per session.** Required by EU AI Act Art. 15, OWASP LLM06, OWASP ASI02.
- **Human-oversight primitives: kill switch, per-decision override, approval gates for write actions.** Required by EU AI Act Art. 14 and Art. 26(2); GDPR Art. 22.
- **AI system card per registered system** with intended purpose, scope, limitations, operator, accountable role. Required by EU AI Act Art. 13; ISO 42001 A.8.
- **Instructions-for-use artefact** consumable by downstream deployers. Required by EU AI Act Art. 13.
- **Training/fine-tune data register with provenance, licence, and quality flags.** Required by EU AI Act Art. 10; ISO 42001 A.7; GDPR Arts. 5, 6, 9.
- **DPIA / AIIA template with cross-reference to EU AI Act Art. 26(9).** Required by GDPR Art. 35 + AI Act Art. 26(9); ISO 42001 A.5.
- **Incident register with structured export** conforming to NIS2 Art. 23 and DORA Art. 19 reporting windows.
- **Vendor / ICT third-party register** with contractual clause tracking. Required by DORA Arts. 28–30; ISO 42001 A.10.
- **Content-provenance labelling on AI-generated record fields** (who, when, which model, which prompt hash). Required by EU AI Act Art. 50 and forthcoming Code of Practice on Transparency.
- **Records of Processing Activities (RoPA)** linked to each AI processing operation. Required by GDPR Art. 30.
- **Regulatory register with versioned citations** for continuous legal-horizon tracking. AI RMF `GV-1.1`; ISO 42001 clause 4.
- **Role model with mandatory separation-of-duties configurations** (the agent that executes a write cannot be the role that approves it).

## Soft recommendations (should-have, best practice but not legally forced)

- **AIBOM/SBOM attachment per model and per MCP tool binding** — strongly recommended by CSA AICM and NIST AI RMF `MAP-4.1`; likely to become mandatory post-2027.
- **CAIQ-for-AI export report** — for vendor questionnaires; easier to ship early than retrofit.
- **MITRE ATLAS control mapping published** in the module security documentation.
- **Cost and token ledger with per-agent quotas** — addresses OWASP LLM10 Unbounded Consumption.
- **Evaluation and red-team artefact storage** per model version — aligns with NIST `MEASURE-2.1/2.7`.
- **Bias-and-fairness evaluation fields** — aligns with NIST `MEASURE-2.11`, CSA AICM Bias & Fairness domain.
- **Watermark / C2PA metadata hooks** on generated outputs — anticipates the Code of Practice on Transparency final version (June 2026).
- **Cryptographic signing of task envelopes** — anchors ASI01 Goal Hijack mitigation and research literature on signed agent actions.
- **Automated cross-walk badges** showing, per control record, how it maps to AI RMF, ISO 42001 Annex A, AI Act article, CSA AICM, MITRE ATLAS. Massively reduces audit cost.
- **Public dashboard export** of the algorithm register — anticipates Dutch algoritmeregister expectations.
- **Memory-isolation and memory-quarantine UI** — directly addresses ASI06 Memory & Context Poisoning; not yet legally required but called out in all agentic-specific standards.

## Open questions for synthesis

1. **Provider vs deployer boundary for substantial modification.** When a customer configures system-prompts, tool bindings, and fine-tuning data through the module, at what point does the customer become a *provider* under EU AI Act Art. 25(1)? The Act leaves "substantial modification" partly undefined; this is where we need legal review, because the compliance footprint differs by an order of magnitude.
2. **Log retention reconciliation.** AI Act Art. 26(6) sets six-months minimum. DORA effectively demands 5+ years. GDPR storage-limitation says "no longer than necessary." GDPR right-to-erasure arguably conflicts with immutable audit. Resolution: segregate pseudonymised audit from personal data; but the exact architecture is standards-ambiguous.
3. **Embedding store and right-to-be-forgotten.** GDPR Art. 17 vs. the practical impossibility of deleting a specific fact from a trained or embedded vector store. EDPB guidance is still evolving. Module should at least support **source-deletion → re-embedding** cycles, but the legal sufficiency of that is not settled.
4. **Art. 50 "machine-readable" marking for AI-generated content.** The standard (C2PA? SynthID-like? watermark?) is not yet fixed; the Transparency Code of Practice will decide. Module should be format-agnostic until mid-2026.
5. **MCP as "substantial modification."** An MCP tool surface that lets an LLM read and write Odoo records arguably changes intended purpose. The AI Office has not spoken on this yet. Conservative default: treat each non-trivial tool binding as requiring an AIIA entry.
6. **SoD in single-tenant SME Odoo deployments.** Many small Odoo customers have only one admin user. True SoD is structurally impossible; we need a *policy override with justification and retention* pattern rather than a hard block.
7. **GPAI downstream obligations.** If the module calls a GPAI model via API, how much of the Art. 53 provider documentation duty flows down to the ERP-side deployer? Art. 25(4) allocates responsibilities along the value chain but leaves concrete pass-through ambiguous.
8. **Interaction of NIS2 and AI Act incident reporting.** A single incident in an AI-enabled critical service may trigger NIS2 24h, DORA 4h initial, AI Act Art. 73 (serious incident) 15-day, GDPR 72h. Module should generate all four reports from one record but the *wording* differs by regime.
9. **Auditability of agentic reasoning traces.** The academic axiom of "verifiability" requires replaying an agent's decision. Non-deterministic LLM outputs break replay; the field is converging on "record inputs + seed + model-version" as a pragmatic substitute but has no legal endorsement yet.
10. **Certification pathway.** ISO 42001 certification bodies are still scarce; accredited CSA STAR-for-AI is nascent; EU AI Act conformity-assessment bodies are being designated through 2026. Until the landscape settles, the module can claim *readiness* but not *certification*.

---

**End of memo.**

*Primary-source versions consulted (non-exhaustive):*
[AI RMF 1.0 Core — NIST](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/),
[NIST AI 600-1 Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf),
[ISO/IEC 42001:2023 preview](https://cdn.standards.iteh.ai/samples/81230/4c1911ebc9a641fcb6ee21aa09c28ad3/ISO-IEC-42001-2023.pdf),
[Regulation (EU) 2024/1689 on EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng),
[OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/),
[OWASP Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/),
[OWASP Top 10 for Agentic Applications (Dec 2025)](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/),
[CSA AI Controls Matrix](https://cloudsecurityalliance.org/artifacts/ai-controls-matrix),
[MITRE ATLAS](https://atlas.mitre.org/),
[ENISA Multilayer Framework](https://www.enisa.europa.eu/publications/multilayer-framework-for-good-cybersecurity-practices-for-ai),
[GDPR Art. 22](https://gdpr-info.eu/art-22-gdpr/).
