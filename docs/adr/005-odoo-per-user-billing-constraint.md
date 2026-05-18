# ADR-005: Odoo per-user billing is a hard constraint, not a design choice

**Status:** Accepted (2026-05-18)
**Type:** Constraint (not a decision the addon can make — a fact the architecture has to absorb)

## Context

Odoo Enterprise (Online, .sh, on-prem) bills per **active Internal User**, roughly €24-76/user/month depending on country and contract. Portal and public users are free but have access restrictions that make them unusable as service accounts. There is **no service account / integration user / robot exemption** in Odoo's pricing — research confirmed no carve-out across the [official pricing page](https://www.odoo.com/pricing), Enterprise breakdowns, or community discussions.

This intersects badly with what AI governance requires. The straightforward "one Odoo user per AI agent" pattern (clean per-agent ACLs, clean audit attribution, clean revocation) hits a real money wall: a customer running 5 agents (cron sync + Claude + ChatGPT + n8n + internal tool) faces €150-380/month in *additional* Odoo licensing fees that buy them no human-seat features. The bot does not need email, calendar, web UI, or chat — but Odoo charges as if it does.

Empirical evidence: pantalytics.odoo.com audit logs show three distinct origins (human UI clicks, MCP Pro cron sync via Python, Claude MCP server) all collapsed to one `user_id=Rutger Hofste` because every integration shares Rutger's API key on Rutger's user. The root cause is not Pantalytics's setup — it's that the cost of separating them is unjustifiably high.

## The constraint, stated

> **Customers will not, and should not, pay Odoo for additional Internal Users solely to enable AI agent governance. Any architecture this addon recommends must work with one paid user shared across multiple agents.**

This is unfair in spirit: a headless bot consuming RPC bandwidth is being billed the same as a human consuming the full Odoo experience. But fairness is not a lever we control. The addon has to route around it.

## Decision

Treat per-user billing as a **hard architectural input**, not a problem to solve at the pricing layer. The addon's recommended deployment patterns must:

1. Default to **one shared Internal User** for all AI agents (typically named `pantalytics-bots@<customer>.com` or similar).
2. Distinguish agents by a primitive **finer-grained than `res.users.id`** — currently API key id ([ADR-006](006-per-api-key-attribution.md)) or self-attested context tag ([ADR-008](008-context-tagging-fallback.md)).
3. Never document a "one user per agent" path as the primary recommendation. It works, but it shifts customer money to Odoo SA for governance value we generate — that's unsellable.

The README, the in-app onboarding, and any sales material must explicitly call out that the addon delivers per-agent governance **without** requiring additional Odoo user licenses.

## Consequences

**Positive**
- The recommended deployment is economically viable. Customers can adopt the addon without an Odoo budget conversation.
- The addon becomes a real product differentiator: "MCP Pro Governance: per-agent audit on a shared user, no extra Odoo seats."
- We sidestep a permanent dependency on Odoo SA's pricing decisions — if Odoo introduces a service-account tier later, we still work; if they don't, we still work.

**Negative**
- Our addon takes on the work of building attribution machinery that Odoo doesn't provide (patching `_check_credentials`, extending `auditlog.http.request`, threading API key identity through views). Real engineering cost.
- The shared-user model is weaker for some compliance scenarios (per-agent record rules become harder; per-agent disclosure under GDPR Art. 15 becomes a query rather than a model lookup). We document where the gap is, but it is a gap.
- If Odoo SA ever changes API-key internals or removes `res.users.apikeys`, our patch breaks. Mitigation: keep the patch minimal and feature-flagged.
- This constraint shapes the entire roadmap. Features that assume "one agent = one user" (e.g. naive per-user record rules for agents) are non-starters and need redesign.

## Escape hatch (for completeness, not recommended)

Customers who actually need cryptographically-isolated per-agent users — typically high-risk regulated industries (banking, healthcare) where the cost of governance ambiguity exceeds €100s/month — can ignore this ADR and create per-agent Internal Users. The addon supports that case; `agent_identity` was never restricted to N:1 with users. We just don't recommend it as the default.

## Sources

- [Odoo Pricing](https://www.odoo.com/pricing)
- [OEC — Odoo Enterprise pricing breakdown](https://oec.sh/odoo-pricing/enterprise)
- [Ventor — Odoo Enterprise license cost reduction](https://ventor.tech/odoo/odoo-enterprise-license-pricing-and-how-to-reduce-cost/)
- Empirical evidence: pantalytics.odoo.com `auditlog.http.request` 2026-05-18, 742 entries all `user_id=Rutger Hofste` across 3 distinct call origins.
