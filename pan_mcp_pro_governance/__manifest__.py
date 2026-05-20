{
    "name": "MCP Pro",
    "summary": "Connect your Odoo with Claude, ChatGPT, Gemini and Copilot - with a full audit trail of every AI action.",
    "description": """
        MCP Pro - Connect your Odoo with Claude, ChatGPT, Gemini, Copilot
        =================================================================

        The MCP server that brings your favourite AI app inside your Odoo -
        with a full audit trail of every action.

        Pull open quotes, follow up with customers, create sales orders,
        reconcile invoices - straight from chat in Claude, ChatGPT, Gemini
        or Microsoft Copilot. Works on desktop and mobile. Works on Odoo
        Online, Odoo.sh and on-premise.

        The MCP Pro server runs outside Odoo (5-minute setup, EU-hosted).
        This addon installs *inside* your Odoo and gives operators what
        the server alone cannot: scoped API keys bound to OCA user roles,
        and an audit trail of every inbound call, powered by OCA Audit Log.

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
        - MCP Pro User (read-only)
        - MCP Pro Manager (administration)

        Roadmap (broader AI governance)
        -------------------------------
        - First-class agent identity registry (provider, owner, lifecycle)
        - Per-agent policies, quotas, risk classification
        - Approval workflows for high-impact actions
        - EU AI Act compliance reporting

        Data handling
        -------------
        - No data leaves your Odoo database
        - No call-home, no telemetry, no third parties
        - Open source (AGPL-3) - audit every line

        Requirements
        ------------
        - Odoo 19.0
        - Python 3.11+
        - OCA `auditlog` 19.0 (installed automatically as a dependency)
    """,
    "author": "Pantalytics B.V. by Rutger Hofste",
    "website": "https://pantalytics.com/apps/odoo-mcp-server",
    "support": "support@pantalytics.com",
    "category": "Productivity",
    "version": "19.0.0.4.3",
    "license": "AGPL-3",
    "depends": [
        "base",
        "mail",
        # auditlog + base_user_role (both OCA) temporarily removed to
        # diagnose apps.odoo.com rescan failure ("unmet dependency ... for
        # series 19.0. Dependency might be invalid."). Runtime is
        # intentionally broken in this revision. Removed in two steps so we
        # could verify the listing only updates once ZERO OCA deps remain.
    ],
    "data": [
        "security/mcp_pro_governance_groups.xml",
        "security/ir.model.access.csv",
        "views/mcp_governance_agent_identity_views.xml",
        "views/mcp_governance_api_call_log_views.xml",
        "views/mcp_governance_apikeys_views.xml",
        "views/mcp_governance_menus.xml",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        "web.assets_tests": [
            "pan_mcp_pro_governance/static/src/js/tours/governance_tour.js",
            "pan_mcp_pro_governance/static/src/js/tours/lifecycle_tour.js",
        ],
    },
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
