{
    "name": "MCP Pro — Audit Log & Scoped API Keys for AI Agents (Claude, ChatGPT, Gemini)",
    "summary": "Audit log and scoped API keys for AI agents in Odoo — Claude, ChatGPT, Gemini, Copilot. Free companion to MCP Pro server.",
    "description": """
        MCP Pro - Audit Log & Scoped API Keys for AI Agents in Odoo
        ===========================================================

        MCP Pro is a hosted MCP server (paid SaaS, EU-based) plus this
        free companion addon. Start fast: connect Claude, ChatGPT, Gemini
        or Microsoft Copilot to your Odoo in under a minute on the hosted
        server — works on Odoo Online, Odoo.sh and on-premise. Install
        this addon when you need governance: scoped API keys bound to
        user roles, and an audit log of every inbound AI call.

        Pull open quotes, follow up with customers, create sales orders,
        reconcile invoices — straight from chat. Works on desktop and
        mobile.

        Features
        --------
        **Audit log (powered by OCA Audit Log):**
        - One row per inbound HTTP request from any AI agent
        - Per-record ORM change log correlated to the originating call
        - Pre-seeded rules for the models AI agents touch most:
          sale.order, res.partner, account.move, crm.lead,
          product.template, stock.picking. Operators can add more.

        **Scoped API keys (powered by OCA Server Backend):**
        - Bind each API key to a single OCA user role
        - The key's effective permissions are exactly that role's groups —
          never broader than the owning user, never broader than the role
        - Suspended and revoked keys fail closed at authentication
        - Last-used timestamp and call counter per key

        **Security groups:**
        - MCP Pro Administrator (read the audit log, configure rules,
          manage all API keys). Any internal user can manage their own
          API keys without this group.

        Data handling
        -------------
        - No data leaves your Odoo database
        - No call-home, no telemetry, no third parties
        - Open source (AGPL-3) - audit every line

        Requirements
        ------------
        - Odoo 19.0
        - Python 3.11+
        - `pan_mcp_auditlog` and `pan_mcp_user_role` (bundled in this
          package, installed automatically as dependencies)
    """,
    "author": "Pantalytics B.V. by Rutger Hofste",
    "website": "https://pantalytics.com/apps/odoo-mcp-server",
    "support": "support@pantalytics.com",
    "category": "Productivity",
    "version": "19.0.1.20.3",
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
        # OCA auditlog + base_user_role are vendored into this repo
        # under renamed module names. The original OCA names are
        # claimed by older Odoo series on apps.odoo.com and cannot be
        # re-uploaded for 19.0 by a different publisher. See ADR-013
        # (which supersedes ADR-012's bundled-sibling approach).
        "pan_mcp_auditlog",
        "pan_mcp_user_role",
    ],
    # NOTE — multi-version (see docs/dev/multi-version-port-plan.md):
    # Odoo parses __manifest__.py with ast.literal_eval, so this list cannot
    # branch on the running version. The few version-specific data files are
    # therefore the ONE legitimate per-release-branch difference. This (19.0)
    # branch loads the 19+ variants; the 18.0 release branch swaps:
    #   - security/groups_privilege_v19.xml  ->  security/groups_legacy.xml
    #   - drops views/mcp_governance_role_views.xml  (res_user_group_ids widget
    #     is 19-only; 18 uses the OCA default flat tags)
    # All Python stays identical across branches via compat.py.
    "data": [
        "security/mcp_pro_governance_groups.xml",
        "security/groups_privilege_v19.xml",
        "security/ir.model.access.csv",
        "views/mcp_governance_api_call_log_views.xml",
        "views/mcp_governance_apikeys_views.xml",
        "views/mcp_governance_auditlog_views.xml",
        "views/mcp_governance_onboarding_views.xml",
        "views/mcp_governance_role_views.xml",
        "views/mcp_governance_menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_backend": [
            "pan_mcp_pro_governance/static/src/js/apikeys_help_banner.xml",
        ],
        "web.assets_tests": [
            "pan_mcp_pro_governance/static/src/js/tours/governance_tour.js",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
