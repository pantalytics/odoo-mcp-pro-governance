# Related Pantalytics Repositories

This module is one leg of a three-repo product family branded **Odoo MCP Pro**.

| Repo | Role | License | Where it runs | How it ships |
|---|---|---|---|---|
| [`odoo-mcp-pro`](https://github.com/pantalytics/odoo-mcp-pro) | Open-source MCP server. Python package `mcp_server_odoo` exposing Odoo to AI agents (Claude, ChatGPT, Cursor, …) over the Model Context Protocol. Single-tenant when self-hosted. Auths to Odoo via XML-RPC + API key. | Elastic 2.0 | Outside Odoo (a Python process on customer infra or pantalytics.com) | pip / Docker / hosted at `pantalytics.com/apps/odoo-mcp-server` |
| [`odoo-mcp-pro-admin`](https://github.com/pantalytics/odoo-mcp-pro-admin) | Closed-source SaaS layer on top. FastAPI admin panel, OAuth 2.1 via Zitadel, Stripe billing (Free / Pro €25/user/mo / Max €100/user/mo), usage tracking + rate limits, encrypted API-key storage, teams/invites. Runtime-overrides parts of the public package. | Proprietary | Pantalytics infra only | Deployed at pantalytics.com — **not installed in customer Odoo** |
| **`odoo-mcp-pro-governance`** (this repo) | Free Odoo addon module. Installs **inside** the customer's Odoo instance. Provides the operator-facing visibility & oversight surface: agent identity registry, append-only ORM audit log, append-only API call log. Companion to the server above — it does not replace the server, it observes and governs it. | LGPL-3 | Inside customer Odoo | **Odoo App Store** (€0) |

## How the three fit together

```
   ┌─────────────────────────────────────────────────────────────┐
   │  Customer's Odoo instance                                   │
   │                                                             │
   │   ┌─────────────────────────────────────────────────────┐  │
   │   │  pan_mcp_pro_governance (this repo)                 │  │
   │   │  - mcp.governance.agent.identity                    │  │
   │   │  - mcp.governance.api.call.log    (append-only)     │  │
   │   │  - mcp.governance.audit.log       (append-only)     │  │
   │   └────────────────────▲────────────────────────────────┘  │
   │                        │ writes via XML-RPC / JSON-RPC     │
   │                        │ when agents act                   │
   └────────────────────────┼────────────────────────────────────┘
                            │
   ┌────────────────────────┴────────────────────────────────────┐
   │  odoo-mcp-pro                            (Elastic 2.0, OSS) │
   │  Stateless MCP server. Receives AI tool calls,              │
   │  proxies them to Odoo via API key.                          │
   └────────────────────────▲────────────────────────────────────┘
                            │ runs alongside / wraps
   ┌────────────────────────┴────────────────────────────────────┐
   │  odoo-mcp-pro-admin                  (Proprietary, hosted)  │
   │  OAuth 2.1, teams, Stripe billing, usage limits.            │
   │  Sells access to the hosted version of the server.          │
   └─────────────────────────────────────────────────────────────┘
```

The governance addon is independent of which tier (Free / Pro / Max) a customer is on — and works equally for the OSS self-hosted server. Anyone running an MCP server against their Odoo can install this addon to get oversight.

## Positioning rules

- **This repo is the "companion" app.** It is €0 on the App Store. It is not a paywall, not a trial, not a teaser.
- **It does not call home.** No telemetry, no signup-from-Odoo flows that POST to Pantalytics. Discreet `mailto:` and an external-link button to the MCP Pro landing page are the only outbound surface, per Odoo App Store vendor guidelines.
- **Outbound URL** for the "Learn more about MCP Pro" CTA: `https://pantalytics.com/apps/odoo-mcp-server` (the canonical MCP Pro landing page; `/en/` prefix has been dropped — language switcher branches from root).
- **The two server repos share Pantalytics' Stripe stack and Zitadel SSO.** This addon shares neither — it stores everything in the customer's Odoo DB and never reaches out.

## Cross-references for future work

- When implementing scoped keys (roadmap v0.3), align field names with `mcp_server_odoo.*` so MCP Pro can read the scope on every call.
- When implementing real API call capture, the writer lives in `odoo-mcp-pro` (or its admin overlay), not here. This addon is the read surface.
- Branding: `Odoo MCP Pro` is the umbrella name; this addon's display name should make clear it is the *governance* / *companion* piece, not the server itself.
