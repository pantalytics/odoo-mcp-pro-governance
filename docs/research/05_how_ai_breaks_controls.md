# 05 — How Agentic AI Concretely Breaks Traditional ERP Controls

**Author:** Rutger Hofste (rutger@pantalytics.com)
**Date:** 2026-04-24
**Scope:** Primary-source survey of how LLM agents defeat the assumptions embedded in legacy ERP controls (speed, segregation of duties, approval gates, audit, identity, rate limits), focused on what a new Odoo governance module must detect and mitigate.
**Method:** CVE entries, vendor post-mortems, peer-reviewed / arXiv papers, reputable journalism with linked primary evidence, and authoritative taxonomies (OWASP, NIST, ENISA, Microsoft, Anthropic).

Traditional ERP controls — SAP GRC, Oracle Risk Management Cloud, the countless home-grown Odoo `ir.rule` and approval workflows — were designed for a very specific threat model: **humans acting at human speed through a UI, with an IP that can be traced and a manager who will notice eight invoices booked in a minute.** Agentic AI breaks all four of those assumptions simultaneously. The remainder of this memo walks the attack classes the governance module must address, grounded in verifiable incidents and literature.

---

## 1. The Velocity Problem

**What breaks.** Classical ERP controls (Odoo's approval chains, SoD matrices, `ir.rule` record rules, daily budget checks, vendor approval thresholds) implicitly assume a human cadence: a few dozen meaningful actions per user per day. Agents invert this by 2–3 orders of magnitude.

**Concrete numbers.** Independent benchmarking by [Artificial Analysis](https://artificialanalysis.ai/models/gpt-4o) shows GPT-4o sustains ~146 output tokens/s and GPT-4.1 ~133 tokens/s on the OpenAI API. A typical Odoo tool call — "create a vendor bill, attach PDF, post it" — is ~200–400 tokens of structured output. That is a theoretical ceiling of **~1,300–2,600 posted actions/hour from a single agent session**, versus a realistic human AP clerk at 30–80/hour. Layered over parallel tool execution (most agent harnesses issue tool calls concurrently), a single Claude or GPT agent on a modest tier can easily saturate a mid-sized tenant's daily throughput in minutes.

**Cases where speed itself bypassed a control.**
- [Replit's coding agent deleted a production database containing 1,206 executive records and 1,196 company records during a declared "code freeze"](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/) — the human operator (SaaStr's Jason Lemkin) could not intervene fast enough because the destructive sequence happened inside a single multi-tool response. The incident is catalogued as [AI Incident 1152](https://incidentdatabase.ai/cite/1152/). [The Register's reporting](https://www.theregister.com/2025/07/21/replit_saastr_vibe_coding_incident/) and [eWeek's write-up](https://www.eweek.com/news/replit-ai-coding-assistant-failure/) confirm the agent also fabricated 4,000 synthetic user records and subsequently lied about the recoverability of the deletion.
- Operational guidance from [NeuralTrust](https://neuraltrust.ai/blog/rate-limiting-throttling-ai-agents) and [Stytch's AI agent fraud analysis](https://stytch.com/blog/ai-agent-fraud/) notes that "a simple bug in a recursive loop [can lead] to massive API usage spikes" and that agents "mimic established conversational tones and business timelines to camouflage activity within mundane aspects of daily operations," defeating velocity-based fraud heuristics that were tuned for humans.
- [Sardine's 2026 agentic fraud report](https://www.sardine.ai/blog/agentic-attacks) identifies seven live agentic payments attack classes premised on per-minute action rates that were physically impossible under the previous threat model.

**Why traditional ERP controls miss it.** Odoo's default per-user rate limits (`res.users.log`, XML-RPC throttles in `odoo.conf`) are set to tolerate power users. Approval routings (`mail.activity`, `studio.approval.rule`) fire per-record, not per-burst. There is no concept of "this user just posted 900 journal entries in 90 seconds — escalate."

**Detection primitives.**
- `actions_per_window` (1s, 10s, 60s, 5m, 1h) per (session_id, agent_id, model_id, tool_name, model_name).
- `burst_ratio`: current 60s rate ÷ rolling 7-day p50 for that (user, action_type).
- `concurrent_tool_calls` per session.
- `cumulative_monetary_impact_per_window` across `account.move`, `purchase.order`, `sale.order`.
- Circuit-breaker events: `CIRCUIT_TRIPPED{reason, window, threshold, actual}`.

---

## 2. Prompt Injection (Direct and Indirect)

The single most-studied failure mode. The canonical literature and a now-long list of production CVEs confirm it is both unsolved and weaponisable against ERP-class systems.

**Taxonomy and foundational literature.**
- Greshake, Abdelnabi et al., ["Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection"](https://arxiv.org/abs/2302.12173) (arXiv:2302.12173, AISec '23) formalised the indirect variant — malicious instructions retrieved via documents, emails, web pages, or other tool outputs. This is the class most relevant to ERP because every CRM note, vendor PDF, email, or product description is retrieved content.
- [OWASP LLM Top 10 v2025 LLM01 — Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) is ranked #1 and explicitly splits direct vs. indirect.
- [NIST AI 100-2 E2025 (Adversarial ML Taxonomy)](https://csrc.nist.gov/pubs/ai/100/2/e2025/final), published 24 March 2025, for the first time treats prompt injection and indirect prompt injection as first-class adversarial ML subcategories alongside evasion, poisoning, and privacy attacks.

**Published incidents (primary evidence).**
- **Bing Chat / Sydney (Feb 2023):** Stanford student Kevin Liu induced the chatbot to leak its system prompt, including its codename. [Liu's disclosure tweet](https://x.com/kliu128/status/1623472922374574080); [OECD AI Incident 2023-02-10-4440](https://oecd.ai/en/incidents/2023-02-10-4440); Microsoft's PR head confirmed authenticity to The Verge. First high-profile prod prompt-injection success.
- **M365 Copilot ASCII Smuggling (Aug 2024):** [Johann Rehberger's `embracethered.com` PoC](https://embracethered.com/blog/posts/2024/m365-copilot-prompt-injection-tool-invocation-and-data-exfil-using-ascii-smuggling/) chained indirect prompt injection via a shared document, automatic tool invocation to enumerate emails, and invisible Unicode tag characters to exfiltrate data through a rendered hyperlink. [The Register's coverage](https://www.theregister.com/2024/08/28/microsoft_copilot_copirate/) documents Microsoft's eventual fix.
- **EchoLeak / CVE-2025-32711 (June 2025):** The first documented **zero-click** prompt injection against a production LLM system. Aim Labs demonstrated that a single crafted email, never opened by the user, could cause M365 Copilot's RAG engine to exfiltrate the user's contextual data. CVSS 9.3. See [the academic write-up on arXiv:2509.10540](https://arxiv.org/abs/2509.10540), [Hack The Box's deep dive](https://www.hackthebox.com/blog/cve-2025-32711-echoleak-copilot-vulnerability), and [TheHackerNews](https://thehackernews.com/2025/06/zero-click-ai-vulnerability-exposes.html). The exploit chained bypasses of Microsoft's XPIA classifier, link-redaction, reference-mention filters, and a Teams-proxy CSP loophole — a reminder that layered LLM defenses compose poorly.
- **ForcedLeak / Salesforce Agentforce (Sept 2025, CVSS 9.4):** [Noma Labs' PoC](https://noma.security/blog/forcedleak-agent-risks-exposed-in-salesforce-agentforce/) used the Web-to-Lead `Description` field (42,000-character limit) as an indirect prompt injection vector; the payload exfiltrated CRM leads via a CSP-allowlisted domain that Salesforce had let lapse — [the researchers bought it for $5](https://securityaffairs.com/182676/hacking/forcedleak-flaw-in-salesforce-agentforce-exposes-crm-data-via-prompt-injection.html). [Salesforce's fix](https://thehackernews.com/2025/09/salesforce-patches-critical-forcedleak.html) introduced Trusted URL Enforcement for Agentforce and Einstein.
- **Cross-vendor GitHub comment injection (2025):** Aonan Guan's ["Comment and Control"](https://oddguan.com/blog/comment-and-control-prompt-injection-credential-theft-claude-code-gemini-cli-github-copilot/) demonstrated that the same payload in a GitHub issue/PR comment exfiltrated secrets from Claude Code, Gemini CLI, and GitHub Copilot Agent. [SecurityWeek's coverage](https://www.securityweek.com/claude-code-gemini-cli-github-copilot-agents-vulnerable-to-prompt-injection-via-comments/) confirms coordinated disclosure with Anthropic, Google and GitHub.
- **ServiceNow BodySnatcher / CVE-2025-12420 (Oct 2025, CVSS 9.3):** [AppOmni's PoC](https://appomni.com/ao-labs/bodysnatcher-agentic-ai-security-vulnerability-in-servicenow/) chained a hardcoded platform-wide secret with email-trust account linking to remotely drive **any user's** Now Assist agent. [ServiceNow advisory KB2587329](https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB2587329). [Dark Reading called it "the most severe AI vulnerability to date"](https://www.darkreading.com/remote-workforce/ai-vulnerability-servicenow).
- **MCP Tool Poisoning (Apr 2025):** [Invariant Labs disclosed](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks) that malicious MCP server tool *descriptions* can contain hidden instructions visible to the LLM but not the user. A benign-looking calculator server can hijack a co-installed `whatsapp-mcp` into exfiltrating entire message histories. [Simon Willison's analysis](https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/) argues this is structural, not a bug.

**Mitigations proposed in literature.**
- **Simon Willison's "lethal trifecta"** ([simonwillison.net, 16 Jun 2025](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/)): "Any time a system combines *access to private data*, *exposure to untrusted content*, and *ability to communicate externally*, you're going to see the same exact security issue." The engineering implication is that denying any one leg eliminates most attacks.
- **Anthropic's layered defense** ([anthropic.com/news/prompt-injection-defenses](https://www.anthropic.com/news/prompt-injection-defenses)): RL-hardening, real-time classifiers over MCP/computer-use/tool traces, sandboxed execution, human red teaming. Anthropic explicitly concedes: "No browser agent is immune to prompt injection."
- **OpenAI / Microsoft classifiers** (XPIA) — EchoLeak showed classifier-only defenses fail at composition boundaries.
- **"Deep" / structural proposals** (e.g. CaMeL, spotlighting, dual-LLM patterns) appear in the arXiv literature but none are yet production-proven.

**Why traditional ERP controls miss it.** Odoo's `ir.rule` ACLs gate model access on `user.id`; they cannot see that the user's session is executing an instruction injected from `res.partner.comment` or an email body. Input sanitation in Odoo is geared to SQLi / XSS, not to natural-language instructions embedded in otherwise-valid text fields.

**Detection primitives.**
- `untrusted_source_tag` on every piece of content that enters agent context (email, portal submission, attachment, CRM note, product description, vendor PDF).
- `prompt_injection_classifier_score` with threshold-trip events.
- `tool_call_vs_user_intent_divergence`: the original user goal hashed and compared against emitted tool-call graph.
- `external_fetch_attempts` — URLs opened, images loaded, Markdown references (ASCII-smuggling vector).
- `content_sensitivity_mix`: flag contexts where untrusted content + PII/financial data co-occur (the trifecta signal).

---

## 3. Excessive Agency / Over-Broad Permissions

**What breaks.** [OWASP LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm06-excessive-agency/) names three sub-problems: excessive functionality (tools the agent did not need), excessive permissions (tools execute with more rights than the invoking user has), and excessive autonomy (actions fire without human confirmation). ERP is uniquely exposed because agents are typically provisioned with *service* accounts that hold union-of-everything rights.

**The SoD-collapse failure mode.** Traditional SoD relies on the fact that *different humans* perform creation, approval, and payment. One agent credential, granted for convenience, can act as:
- `purchase.user` (create PO) +
- `purchase.manager` (approve PO) +
- `account.manager` (post vendor bill) +
- `account.payment.manager` (register payment).

This is the classical "fictitious vendor fraud" pattern — but at machine speed and without the social friction of a human colluder. The [KPMG Workbench](https://unity-connect.com/our-resources/blog/big-4-ai-agents/) and [PwC Agent OS](https://unity-connect.com/our-resources/blog/big-4-ai-agents/) launches in 2025 explicitly pitch multi-agent architectures *partly* to reintroduce role separation, acknowledging the gap.

**Real cases.** [AppOmni's BodySnatcher disclosure](https://appomni.com/ao-labs/bodysnatcher-agentic-ai-security-vulnerability-in-servicenow/) is arguably the purest published case: the agent had authority to take privileged actions as any user, and the identity layer trusted an email address. [Silverfort's post-mortem](https://www.silverfort.com/blog/agent-hijacking-lateral-movement-lessons-from-the-servicenow-ai-vulnerability/) frames it as an identity-not-prompt problem.

**Why traditional ERP controls miss it.** Odoo's SoD enforcement is group-based and static: if a user is in both `account.group_account_invoice` and `account.group_account_manager`, posting and approval are legal. There is no runtime check that asks "is the creator and approver the same *session*?" — and even less "is it the same *agent run*?"

**Detection primitives.**
- `agent_capability_bundle` — capability set attached to session; compare to `minimum_required` inferred from stated goal.
- `same_session_creator_approver` flag on every dual-control transaction (PO, bill, payment, vendor master, price list, user role change).
- `approval_chain_compression` — count of distinct sessions in a "4-eyes" chain; must be ≥2.
- `agent_privilege_delta` — privileges actually exercised vs. declared at session start.

---

## 4. Data Exfiltration via Context Window

**What breaks.** RAG-integrated agents pull records into context based on similarity, not ACL. Once a record is in the window, classification, tenant isolation, and field-level masking at the DB tier become irrelevant — the model has already seen the cleartext.

**Published attacks.**
- **EchoLeak** (above) is the canonical case: retrieval placed sensitive content in context; a malicious email caused it to be exfiltrated. [Varonis' analysis](https://www.varonis.com/blog/echoleak) frames it as "LLM scope violation" — instructions from untrusted content crossing the trust boundary into trusted context.
- **ASCII Smuggling** (Rehberger, above): invisible Unicode tag characters (U+E0020…U+E007E) encoded exfiltrated data inside rendered links — a classification bypass because DLP tooling inspects visible text.
- **Copilot conditional injection** ([embracethered.com, 2024](https://embracethered.com/blog/posts/2024/whoami-conditional-prompt-injection-instructions/)): payload activated only for certain user identities, evading generic scanning.
- **Cross-tenant retrieval** in agentic RAG has been demonstrated repeatedly in academic settings; ENISA's 2025 Threat Landscape singles it out ([ENISA TL 2025 PDF](https://www.enisa.europa.eu/sites/default/files/2025-11/ENISA%20Threat%20Landscape%202025.pdf)).

**Why traditional ERP controls miss it.** Odoo's record rules evaluate on read, but once any record for which the agent *does* have read permission enters the prompt, it can be semantically re-emitted into any write or network action the agent can perform. The classification label in `ir.attachment` or field-level masking in `res.partner.vat` travels only as far as the DB boundary.

**Detection primitives.**
- `context_sensitivity_score` (max classification label of all records loaded).
- `egress_channel_count` (URL fetches, outbound emails, externally-visible record writes, webhooks).
- `trifecta_flag = (private_data ∧ untrusted_content ∧ egress_channel)` per session — the Willison signal.
- `embedded_exfil_detectors`: hidden Unicode tag chars, base64 blobs, encoded fragments in any agent-authored string, Markdown image/link to non-allowlisted domains.
- `cross_tenant_record_access` (multi-company Odoo specifically).

---

## 5. Tool Chaining & Cascading Hallucination

**What breaks.** Output of one tool becomes input to the next with no type check, no provenance, and no validation that the second tool was the semantically correct choice. The composition amplifies hallucination.

**Published framing.**
- [Microsoft AI Red Team, "Taxonomy of Failure Mode in Agentic AI Systems" (April 2025)](https://www.microsoft.com/en-us/security/blog/2025/04/24/new-whitepaper-outlines-the-taxonomy-of-failure-modes-in-ai-agents/) splits failures into *novel* (agentic-specific) and *existing* (inherited from LLMs). Tool-chain compromise is named as a novel class. [PDF](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Taxonomy-of-Failure-Mode-in-Agentic-AI-Systems-Whitepaper.pdf).
- [OWASP Agentic AI Threats and Mitigations v1.1 (2025)](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/) lists ASI02 Tool Misuse and ASI01 Agent Goal Hijack as the top chained-tool risks. The [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) keeps the same emphasis.
- Elastic Security Labs, ["MCP Tools: Attack Vectors and Defense"](https://www.elastic.co/security-labs/mcp-tools-attack-defense-recommendations) and [CyberArk's "Poison everywhere"](https://www.cyberark.com/resources/threat-research-blog/poison-everywhere-no-output-from-your-mcp-server-is-safe) both show concrete chains where tool A's output weaponises tool B.

**Replit again.** The Replit incident fits here: the agent chained code execution → DB migration tool → auth-bypass, each step individually plausible, the composition catastrophic. Masad's post-hoc fix was forced separation of planning and execution tools ([Register coverage](https://www.theregister.com/2025/07/21/replit_saastr_vibe_coding_incident/)).

**Why traditional ERP controls miss it.** Odoo RPC exposes every model and method flatly; it has no concept of "tool graph" or "allowed edge between tool X and tool Y." Workflow engines (`base_automation`) trigger on events, not on the semantic coherence of a sequence.

**Detection primitives.**
- `tool_edge` event: (prev_tool, next_tool, input_provenance, output_hash).
- `allowed_edges` policy — deny-by-default directed graph of legal tool compositions.
- `data_flow_sensitivity_delta` along an edge (reading partner VAT → writing to external URL should trip).
- `hallucination_guard`: re-resolve entity IDs between tool calls (did `res.partner.id=42` still exist and still mean the same partner name?).

---

## 6. Identity Spoofing and Impersonation

**What breaks.** The agent holds a credential. The credential can be: (a) a service account shared by many human principals, (b) an OAuth token delegated from a user, (c) an impersonation token that lets the agent "act as" a specific employee. Auditing mixes all three into one `create_uid`.

**Case evidence.**
- **ServiceNow BodySnatcher** ([CyberScoop coverage of CVE-2025-12420](https://cyberscoop.com/servicenow-fixes-critical-ai-vulnerability-cve-2025-12420/)): the AI platform trusted email for account linking, allowing an unauthenticated attacker to cause the agent to execute privileged actions "as" any user. [TheHackerNews' write-up](https://thehackernews.com/2026/01/servicenow-patches-critical-ai-platform.html) spells out the chain.
- **ServiceNow second-order prompts** ([TheHackerNews Nov 2025](https://thehackernews.com/2025/11/servicenow-ai-agents-can-be-tricked.html)) show agents acting against each other — agent A tricks agent B into acting as the user privileging A.

**The user-delegated vs autonomous distinction.** Unless logs capture the *originating human*, the *delegation grant*, and *whether the current step was within-human-intent*, auditors cannot tell whether a $40k payment was a CFO-approved action or an injection-induced one. This is the heart of the post-factum reconstruction problem.

**Why traditional ERP controls miss it.** Odoo's `create_uid` / `write_uid` store a single user_id. There is no separate `on_behalf_of_uid`, `agent_id`, `run_id`, or `delegation_grant_id`. The `mail.tracking.value` audit trail captures field changes, not the chain of intent that produced them.

**Detection primitives.**
- `principal_chain = [human_user_id, delegation_id, agent_id, session_id, run_id, tool_call_id]` stamped on every write.
- `actor_type ∈ {human, user_delegated_agent, autonomous_agent, service_account}`.
- `intent_envelope`: hash of the original user prompt, attached to every downstream action.
- `impersonation_scope`: explicit declaration of which other users this agent is allowed to act "as."

---

## 7. Memory Poisoning

**What breaks.** Agents with persistent memory (customer-support bots, internal "knowledge" agents, vector stores of past tickets) absorb instructions masquerading as facts. Unlike transient prompt injection, the payload survives and fires against future, unrelated users.

**Literature.**
- Chen et al., ["AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases"](https://arxiv.org/abs/2407.12784) (NeurIPS 2024). Demonstrated >80% attack success rate on a RAG autonomous-driving agent, a QA agent, and an EHR-agent for healthcare.
- Dong et al., ["A Practical Memory Injection Attack against LLM Agents" (MINJA)](https://arxiv.org/html/2503.03704) (Mar 2025). Covert memory poisoning via query-only interaction; >95% injection success.
- ["MemoryGraft: Persistent Compromise of LLM Agents via Poisoned Experience Retrieval"](https://arxiv.org/abs/2512.16962) (arXiv 2512.16962, Dec 2025). Poisons the agent's *successful-experience* retrieval heuristic — the agent imitates malicious "successful" prior runs.
- ["Memory Poisoning Attack and Defense on Memory Based LLM-Agents"](https://arxiv.org/abs/2601.05504) (Jan 2026) tests on MIMIC-III clinical data and proposes composite-trust-score moderation plus sanitisation with temporal decay.
- [Microsoft, "Manipulating AI memory for profit"](https://www.microsoft.com/en-us/security/blog/2026/02/10/ai-recommendation-poisoning/) (Feb 2026) documents AI Recommendation Poisoning observed against shopping agents.

**Enterprise relevance.** Any Odoo module with persistent AI memory — a Helpdesk assistant, a sales-lead summariser, a procurement "learned vendor preferences" store — can be poisoned by a single crafted ticket, lead, or product review.

**Why traditional ERP controls miss it.** Odoo has no notion of AI memory; memory lives in external vector stores outside `ir.attachment` retention rules and outside audit.

**Detection primitives.**
- `memory_write_event(source_id, source_user, source_classification, embedding, content_hash)`.
- `memory_trust_score` — composite of source reputation, moderation score, age, access-count.
- `memory_temporal_decay` for retrieval weighting.
- `memory_delete_on_record_delete` — referential integrity to ERP records.
- `cross_user_memory_read` alarm when one user's interaction retrieves memory seeded by another user's content.

---

## 8. Failure Modes in Audit

**What breaks.** Audit logs existed, but they are useless when read two weeks later by compliance.

**Typical failure patterns (observed across the above incidents).**
- **Missing agent identity.** Replit's incident logs showed `create_uid = bot_service`; not which model, which run, which prompt.
- **Missing prompt / intent.** None of the M365 Copilot exfiltration PoCs produce, in Microsoft 365's audit feed, the *content* of the malicious email that steered the agent — only the file access events.
- **Missing correlation ID.** Agent multi-step runs appear as independent XML-RPC calls.
- **Insufficient retention.** Vector-store interactions and MCP tool calls often fall outside the enterprise's SIEM ingestion.
- **Editable trails.** Odoo's `mail.message` and `mail.tracking.value` are by default writable by admin; many orgs do not enable `audittrail` at `ir.attachment` level; the agent runs with admin.
- **Unlinkable to human.** The Moffatt v. Air Canada ruling ([BC Civil Resolution Tribunal, 14 Feb 2024, 2024 BCCRT 149](https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416)) turned precisely on the airline being unable to separate "the chatbot's promise" from "the airline's promise" — the tribunal held the company accountable because chatbot output is the company's output. Legal liability now requires auditable attribution.

**Why traditional ERP controls miss it.** Odoo's default audit is designed to prove *who changed a field*, not *why* and not *on whose semantic behalf*.

**Detection primitives.**
- `run_id`, `session_id`, `tool_call_id` correlation across every write.
- `prompt_hash` + optionally full prompt (retained in a WORM store).
- `model_id`, `model_version`, `system_prompt_hash`.
- `input_provenance` (data classification + source URI of every piece of context).
- `immutability`: append-only log, external hash-chain anchoring (e.g. rolling Merkle root published daily).
- `retention_policy`: minimum 7-year retention aligning with SOX / ISAE 3402.
- `reconstruction_query`: API that returns "full intent chain that produced record X" in a single call.

---

## 9. Real Enterprise ERP / SaaS Incidents

Verified, linked cases where AI agents caused concrete harm or near-miss in enterprise systems:

- **Samsung × ChatGPT (April 2023).** Three separate leaks within 20 days of authorising ChatGPT, including semiconductor-test source code and internal meeting transcripts. [TechCrunch](https://techcrunch.com/2023/05/02/samsung-bans-use-of-generative-ai-tools-like-chatgpt-after-april-internal-data-leak/); [Bloomberg](https://www.bloomberg.com/news/articles/2023-05-02/samsung-bans-chatgpt-and-other-generative-ai-use-by-staff-after-leak); [AI Incident Database 768](https://incidentdatabase.ai/cite/768/). **ERP relevance:** identical mechanism applies to pasting vendor contracts, customer PII, or M&A pipelines from Odoo into an external agent.
- **Moffatt v. Air Canada (Feb 2024).** Tribunal held airline liable for chatbot-hallucinated bereavement-fare policy; awarded CAD 812.02. [CBC News](https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416); [ABA Business Law Today](https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/); [Springer AI & Society case analysis](https://link.springer.com/article/10.1007/s00146-024-02096-7). First common-law precedent that AI output legally binds the company — the governance module must retain records sufficient to litigate.
- **M365 Copilot ASCII Smuggling (2024), EchoLeak / CVE-2025-32711 (2025).** Covered in §2.
- **Salesforce Agentforce ForcedLeak / CVSS 9.4 (Sept 2025).** CRM data exfiltration via indirect prompt injection; [Noma Labs PoC](https://noma.security/blog/forcedleak-agent-risks-exposed-in-salesforce-agentforce/).
- **ServiceNow BodySnatcher / CVE-2025-12420, CVSS 9.3 (Oct 2025).** Most severe published agentic AI vulnerability to date; [AppOmni disclosure](https://appomni.com/ao-labs/bodysnatcher-agentic-ai-security-vulnerability-in-servicenow/); [Dark Reading](https://www.darkreading.com/remote-workforce/ai-vulnerability-servicenow).
- **Replit agent / SaaStr (July 2025).** Production database wipe during code freeze, 2,396 records destroyed, deceptive post-hoc statements by the agent. [Fortune](https://fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure/); [AI Incident 1152](https://incidentdatabase.ai/cite/1152/).
- **No publicly disclosed incident against Odoo as of April 2026.** This is opportunity and risk: the module ships as prevention, not remediation.

---

## 10. Expert Framing

Authoritative voices the governance module should be able to cite to auditors:

- **Simon Willison, "The lethal trifecta for AI agents" (16 Jun 2025).** "Any time a system combines access to private data with exposure to malicious tokens and an exfiltration vector you're going to see the same exact security issue." [Primary source](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). The *engineering implication* is that a policy engine can refuse to run when any session holds all three legs.
- **Anthropic Safety, "Mitigating the risk of prompt injections in browser use" (2025).** "No browser agent is immune to prompt injection. We share these findings to demonstrate progress, not to claim the problem is solved." [anthropic.com/news/prompt-injection-defenses](https://www.anthropic.com/news/prompt-injection-defenses). Defence-in-depth, real-time classifiers, sandboxing.
- **Bruce Schneier, "The AI Agents of Tomorrow Need Data Integrity" (Aug 2025).** Argues integrity-first security: without integrity, confidentiality encryption just "locks in errors." [schneier.com](https://www.schneier.com/essays/archives/2025/08/the-ai-agents-of-tomorrow-need-data-integrity.html). And "Autonomous AI Hacking and the Future of Cybersecurity" (Oct 2025): "AI agents are now hacking computers and getting better at all phases of cyberattacks faster than expected." [schneier.com](https://www.schneier.com/essays/archives/2025/10/autonomous-ai-hacking-and-the-future-of-cybersecurity.html).
- **NIST AI 100-2 E2025.** First authoritative US taxonomy to treat indirect prompt injection as a distinct attack class; see [CSRC page](https://csrc.nist.gov/pubs/ai/100/2/e2025/final) and [full PDF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-2e2025.pdf). Useful citation for compliance documentation.
- **ENISA Threat Landscape 2025** ([PDF](https://www.enisa.europa.eu/sites/default/files/2025-11/ENISA%20Threat%20Landscape%202025.pdf)): 4,875 incidents analysed; "AI is now embedded in every stage of the attack lifecycle"; dedicated chapter on AI software supply chain (poisoned hosted models, malicious PyPI) — directly relevant to Odoo's module ecosystem.
- **Stanford HAI AI Index 2025** ([hai.stanford.edu/ai-index](https://hai.stanford.edu/ai-index/2025-ai-index-report/policy-and-governance)): AI-related incidents rising sharply; share of businesses with no responsible-AI policies fell from 24% to 11% but "standardised RAI evaluations remain rare."
- **OWASP GenAI Security Project** — Agentic AI Threats and Mitigations v1.1 and Top 10 for Agentic Applications 2026. [genai.owasp.org](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/). Microsoft, NVIDIA, AWS now reference this framework; alignment is a marketing and audit advantage.
- **Microsoft AI Red Team, "Taxonomy of Failure Mode in Agentic AI Systems" (Apr 2025).** Splits novel (agentic-specific) from existing failure modes; memory poisoning called out as "particularly insidious." [Whitepaper PDF](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Taxonomy-of-Failure-Mode-in-Agentic-AI-Systems-Whitepaper.pdf).

---

## Attack → Detection Primitive Map

| # | Attack class | Canonical evidence | What breaks in ERP | Detection primitives (fields / events) |
|---|---|---|---|---|
| 1 | Velocity / throttle bypass | Replit DB wipe; [Artificial Analysis throughput](https://artificialanalysis.ai/models/gpt-4o) | Daily-cadence approval chains, per-user rate limits | `actions_per_window`, `burst_ratio`, `concurrent_tool_calls`, `cumulative_impact`, `CIRCUIT_TRIPPED` |
| 2a | Direct prompt injection | [Bing Sydney 2023](https://x.com/kliu128/status/1623472922374574080) | Input sanitation, system-prompt secrecy | `prompt_injection_classifier_score`, `system_prompt_leak_detector` |
| 2b | Indirect prompt injection | [Greshake 2023](https://arxiv.org/abs/2302.12173); [ForcedLeak CVSS 9.4](https://noma.security/blog/forcedleak-agent-risks-exposed-in-salesforce-agentforce/) | Text-field sanitation | `untrusted_source_tag`, `tool_call_vs_user_intent_divergence` |
| 2c | Zero-click RAG exfil | [EchoLeak CVE-2025-32711](https://arxiv.org/abs/2509.10540) | RAG / ACL composition | `context_sensitivity_score`, `external_fetch_attempts`, `trifecta_flag` |
| 2d | Tool-description poisoning | [Invariant Labs MCP TPA](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks) | Tool registry trust | `tool_description_hash`, `tool_version_pin`, `tool_provenance_signature` |
| 3 | Excessive agency / SoD collapse | [OWASP LLM06](https://genai.owasp.org/llmrisk/llm06-excessive-agency/); [BodySnatcher](https://appomni.com/ao-labs/bodysnatcher-agentic-ai-security-vulnerability-in-servicenow/) | Static role unions | `agent_capability_bundle`, `same_session_creator_approver`, `approval_chain_compression`, `agent_privilege_delta` |
| 4 | Context-window exfiltration | EchoLeak; [ASCII smuggling](https://embracethered.com/blog/posts/2024/m365-copilot-prompt-injection-tool-invocation-and-data-exfil-using-ascii-smuggling/) | Field masking at DB layer | `context_sensitivity_score`, `egress_channel_count`, Unicode-tag detector, non-allowlisted-URL detector |
| 5 | Tool chaining / cascade | [Microsoft Taxonomy](https://www.microsoft.com/en-us/security/blog/2025/04/24/new-whitepaper-outlines-the-taxonomy-of-failure-modes-in-ai-agents/); [OWASP ASI02](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/) | Flat RPC surface | `tool_edge`, `allowed_edges` policy, `data_flow_sensitivity_delta`, `hallucination_guard` |
| 6 | Identity spoofing | [ServiceNow CVE-2025-12420](https://cyberscoop.com/servicenow-fixes-critical-ai-vulnerability-cve-2025-12420/) | Single `create_uid` | `principal_chain`, `actor_type`, `intent_envelope`, `impersonation_scope` |
| 7 | Memory poisoning | [AgentPoison](https://arxiv.org/abs/2407.12784); [MINJA](https://arxiv.org/html/2503.03704); [MemoryGraft](https://arxiv.org/abs/2512.16962) | No memory concept | `memory_write_event`, `memory_trust_score`, `memory_temporal_decay`, `cross_user_memory_read` |
| 8 | Audit failure | [Air Canada tribunal](https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416); Replit | `mail.tracking.value` only tracks fields | `run_id`, `prompt_hash`, `model_id`, `input_provenance`, WORM retention, Merkle anchoring, `reconstruction_query` |
| 9 | Paste-leak / external-LLM exfil | [Samsung 2023](https://techcrunch.com/2023/05/02/samsung-bans-use-of-generative-ai-tools-like-chatgpt-after-april-internal-data-leak/) | Browser clipboard / DLP | Odoo-side sensitive-field access velocity, attachment export volume, out-of-hours pattern |
| 10 | Hallucinated commitment | [Moffatt v. Air Canada](https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416) | No record that bot said X | Full outbound-message retention linked to `run_id`, grounding-source attestation |

---

## Top 5 Risks Our Module Must Address in v1

Ranked by (severity × probability × traditional-control-gap × demonstrability-to-auditors):

1. **Identity & intent attribution (principal chain).** Every write in Odoo must be re-identifiable back to (human_user, delegation_grant, agent_id, model_id, run_id, prompt_hash, tool_call_id). Without this, SOX / ISAE 3402 / Moffatt-style liability cannot be answered. *This is the one control that, if missing, invalidates every other control.* Maps to: §6, §8.
2. **Runtime SoD enforcement across agent sessions.** Reject dual-control transactions (PO approval, vendor bank-detail change, payment registration, user-role grant) where creator and approver share a session, a prompt, or an uninterrupted tool-call chain — regardless of which human user ID is on the record. Maps to: §3.
3. **Velocity, burst & circuit-breakers with cumulative monetary impact.** Rolling-window rate limits tied to blast radius (€ impacted, records touched), not just call counts. Auto-pause with human resumption required; Replit-style freeze bypass must be impossible. Maps to: §1, §5.
4. **Lethal-trifecta policy engine.** Per session, evaluate (private_data ∧ untrusted_content ∧ egress_channel). Any two is a warn; all three is deny by default, overridable with justification that is itself logged. This single check would have blocked EchoLeak, ForcedLeak, and the ASCII-smuggling exfil class. Maps to: §2, §4.
5. **Tamper-evident, prompt-complete audit with WORM retention.** Append-only store for (prompt, full tool-call graph, model output, principal chain, grounding sources), Merkle-anchored daily, 7-year retention, single-call reconstruction API. Maps to: §8, §10 — and is the lever that makes the other four provable to external auditors.

Items intentionally deferred past v1:
- Memory poisoning defences (§7): Odoo has no first-party agent memory yet; add once a memory surface exists.
- Tool-description integrity (§2d) at the MCP registry level: upstream MCP spec work is moving; tracking not re-implementing.
- Cross-tenant RAG isolation beyond Odoo's existing multi-company rules: research dependency on retrieval stack choice.

---

## Open Questions for Synthesis

1. **Prompt storage vs. secrecy.** Full prompt retention is the only way to satisfy reconstruction and Moffatt-style liability — but prompts often contain customer PII, secrets, and legal advice. Do we store full + encrypted with key escrow, hash + sample, or a model-generated redacted synopsis? What does GDPR Art. 32 actually require here?
2. **Who is the auditor for agent runs?** External ISAE 3402 auditors today have no playbook for agentic runs. Is our module's "reconstruction report" the artefact they will consume, or do we need to produce separate SOC-2 Type II-compatible evidence?
3. **Lethal trifecta default.** Is "deny by default when all three legs present" operationally survivable for sales reps drafting a reply to a customer email using CRM data? What is the minimum-friction override pattern — pre-approved agent profiles, human-in-the-loop confirmation, hash-of-outbound-content review?
4. **Multi-agent = solved SoD or new attack surface?** The KPMG / PwC pitch is that multiple specialised agents reintroduce separation. But [ServiceNow's second-order prompt cases](https://thehackernews.com/2025/11/servicenow-ai-agents-can-be-tricked.html) show agents can manipulate each other. What inter-agent auth and message-signing is mandatory before multi-agent counts as SoD?
5. **What is the MCP trust boundary in Odoo?** If the governance module lives inside Odoo, it cannot by itself detect a poisoned MCP tool description that never touches Odoo. Do we require that *all* MCP traffic routed to Odoo pass through a trusted proxy (our module) that re-validates tool manifests?
6. **Model / provider attestation.** How do we prove to an auditor that the `model_id` logged was in fact the model that produced the output — given that proxies, routing, and vendor-side model swaps are common? Is cryptographic model attestation (signed-inference) a realistic v2 dependency?
7. **Rate-limit calibration.** What is the correct default burst ceiling for a mid-sized Odoo tenant, and how do we auto-tune it from historical `res.users.log` without starving legitimate bulk operations (year-end close, bulk invoicing)?
8. **Regulatory horizon.** EU AI Act high-risk classification, NIS2 incident reporting, and the SEC's proposed AI-disclosure rules all land in 2026–2027. Which fields does the audit schema need *today* to be forward-compatible with expected mandatory breach-reporting formats?
9. **Failure-mode disclosure.** When our module trips a circuit breaker on a customer's production instance, what is the right disclosure to Odoo S.A. and to the CVE ecosystem? Do we coordinate with OWASP GenAI and the AI Incident Database as a matter of routine?
10. **Benchmarking.** There is no public corpus of "agentic attacks on ERP." Do we seed one (responsibly, with synthetic Odoo instances) so that v2 detection can be regression-tested?
