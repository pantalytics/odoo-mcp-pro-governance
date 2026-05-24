# ADR-014: No live-chat widget on the in-app Get Started page

**Status:** Accepted (2026-05-22)

## Context

The MCP Pro SaaS marketing site at `pantalytics.com/apps/odoo-mcp-server`
runs a live-chat widget. The question came up whether the same widget
should also run on this addon's in-app **Get Started** page
([mcp_governance_onboarding_views.xml](../../pan_mcp_pro_governance/views/mcp_governance_onboarding_views.xml)),
so a customer with a fresh install can ask questions without leaving
their Odoo.

Technically achievable: inject a third-party chat `<script>` into a
`web.assets_backend` entry scoped to this view, or render it via an
OWL component embedded in the form.

The relevant constraints:

- The Get Started page is rendered **inside the customer's Odoo
  instance**, not on our domain. A chat widget there beacons from the
  customer's browser to a third-party chat host on every page open.
- [CLAUDE.md](../../CLAUDE.md) development principle 4: **no
  call-home**. Telemetry, auto-signup and external POSTs are
  forbidden by both the App Store guidelines and our own positioning
  for the free €0 companion app.
- App Store reviewers reject €0 listings that load external scripts
  from the addon — same class of issue that blocks `https://`
  anchors in `static/description/index.html`.
- The page already has two acceptable escape hatches: a
  `mailto:support@pantalytics.com` link and an "Already set up? Get
  started →" link to a public Odoo Knowledge article on
  `pantalytics.odoo.com`. Both are passive — no script execution, no
  beacon at page load.

## Decision

Do **not** embed a live-chat widget on the in-app Get Started page.
Support contact from inside the installed addon stays passive:
`mailto:` and external anchors that open in a new tab only.

The SaaS marketing site keeps its live chat — that runs on our own
domain, where the call-home rule does not apply.

## Consequences

**Positive**

- App Store review surface stays clean. No external script load from
  inside the addon to flag.
- Customers' Odoo instances do not beacon to our chat host on every
  Get Started page open. No GDPR/privacy footprint added by the
  governance app itself.
- The in-app surface stays consistent with development principle 4
  ("no call-home"). No need to carve out an exception that would
  weaken the rule for later features.

**Negative**

- Slower support loop than the SaaS. A customer with a question in
  the installed addon has to click `mailto:` or navigate to the
  public Knowledge article, instead of typing into a chat bubble.
- Two different support UX between the two surfaces (chat on SaaS,
  email on addon) — minor cognitive cost for customers using both.

## Alternatives considered

- **Embed the same chat widget the SaaS uses.** Rejected for the
  call-home reason above.
- **Add a "Chat with us →" button that opens
  `pantalytics.com/chat` in a new tab.** Technically clean (passive
  link, no embedded script, indistinguishable from the existing
  "Sign up →" button on the same page). Parked: the existing
  `mailto:` + Knowledge link already cover the same need, and adding
  a third button clutters the page without solving a different
  problem. Revisit if support inbound volume shows email is the
  bottleneck.
- **Wait until App Store positioning relaxes.** No reason to expect
  it will; the rule is structural to the €0 companion strategy.

## Sources

- [CLAUDE.md](../../CLAUDE.md) — development principles 3 and 4, App
  Store positioning rules.
- [Get Started view](../../pan_mcp_pro_governance/views/mcp_governance_onboarding_views.xml)
  — current passive-link layout.
- Conversation 2026-05-22 with Rutger.
