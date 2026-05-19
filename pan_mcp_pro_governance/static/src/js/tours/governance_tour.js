/** @odoo-module */

import { registry } from "@web/core/registry";

/**
 * Smoke tour for pan_mcp_pro_governance.
 *
 * Drives the UI a fresh-install reviewer would see:
 *   1. Open the MCP Pro app from the home screen.
 *   2. Navigate to Audit Log; verify the empty-state placeholder.
 *   3. Navigate to API Keys; verify the empty-state placeholder.
 *
 * Driven from tests/test_governance_tour.py via HttpCase.start_tour().
 */
registry.category("web_tour.tours").add("pan_mcp_pro_governance.smoke", {
    test: true,
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_app[data-menu-xmlid='pan_mcp_pro_governance.menu_mcp_governance_root']",
            content: "Open the MCP Pro app",
            run: "click",
        },
        {
            trigger: "[data-menu-xmlid='pan_mcp_pro_governance.menu_mcp_governance_audit_log']",
            content: "Navigate to Audit Log",
            run: "click",
        },
        {
            trigger: ".o_view_nocontent_smiling_face",
            content: "Audit Log empty state visible",
        },
        {
            trigger: "[data-menu-xmlid='pan_mcp_pro_governance.menu_mcp_governance_apikeys']",
            content: "Navigate to API Keys",
            run: "click",
        },
        {
            trigger: ".o_view_nocontent_smiling_face",
            content: "API Keys empty state visible",
        },
    ],
});
