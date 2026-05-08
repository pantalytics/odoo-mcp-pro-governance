# -*- coding: utf-8 -*-
{
    "name": "MCP Pro",
    "summary": "Companion to MCP Pro - the AI connector for Odoo. Agent identities, audit log, API call log. Works with Claude, ChatGPT, Cursor, Gemini.",
    "description": """
        MCP Pro - AI Connector Governance for Odoo
        ===========================================

        **This is the free companion app to MCP Pro, the AI connector for Odoo.**

        The actual MCP server - which connects your Odoo to Claude, ChatGPT,
        Cursor, Gemini, Copilot and any other MCP-compatible AI tool - runs
        outside Odoo. This addon installs *inside* your Odoo and gives
        operators what the server alone cannot: a first-class registry of
        every AI agent, an append-only audit trail, and a per-request API
        call log. It is the oversight surface for AI-driven access to your
        ERP, whether you self-host the server or run a hosted equivalent.

        Why this module?
        ----------------
        Standard Odoo was designed for humans clicking through forms. When an
        AI agent fires 5,000 actions per hour against the same user account,
        the gaps show:

        1. No first-class "agent" identity - API keys inherit full user permissions.
        2. Audit trails record field changes, not which prompt drove the decision.
        3. Segregation of Duties breaks when one agent can create AND approve.
        4. No concept of scoped, rate-limited, rotating credentials.

        This module fills those gaps. It does not replace Odoo's ACLs - it
        instruments around them.

        Features
        --------
        **Agent identities:**
        - First-class model for every AI agent touching your data
        - Owner, sponsor, provider, lifecycle state (draft/active/suspended/revoked)
        - Shadow res.users binding so Odoo ACLs still apply
        - Last-seen tracking

        **Append-only audit log:**
        - Every agent action writes an immutable row
        - Agent identity, acting user, action, model, record, request id, prompt hash
        - Manager cannot edit or delete - AccessError by design

        **Append-only API call log:**
        - One row per inbound MCP / API call - method, path, tool, status, duration
        - Joined to the audit log via request id
        - Filters: today, errors, slow (>1s); group by agent, tool, status

        **Security groups:**
        - MCP Governance User (read-only)
        - MCP Governance Manager (administration)

        Data handling
        -------------
        - No data leaves your Odoo database
        - No call-home, no telemetry, no third parties
        - Open source (LGPL-3) - audit every line

        Requirements
        ------------
        - Odoo 19.0
        - Python 3.11+
    """,
    "author": "Pantalytics B.V. by Rutger Hofste",
    "website": "https://www.pantalytics.com/apps/mcp-pro-governance/",
    "support": "support@pantalytics.com",
    "category": "Productivity",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "security/mcp_pro_governance_groups.xml",
        "security/ir.model.access.csv",
        "views/mcp_governance_agent_identity_views.xml",
        "views/mcp_governance_api_call_log_views.xml",
        "views/mcp_governance_audit_log_views.xml",
        "views/mcp_governance_menus.xml",
    ],
    "assets": {
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
