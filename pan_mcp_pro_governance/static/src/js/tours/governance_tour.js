/** @odoo-module */

import { registry } from "@web/core/registry";

/**
 * Smoke tour for pan_mcp_pro_governance.
 *
 * Drives the UI a fresh-install reviewer would see:
 *   1. Open the MCP Pro app from the home screen.
 *   2. Navigate to API Call Log.
 *   3. Verify the empty-state placeholder renders.
 *   4. Navigate to Agent Identities.
 *   5. Verify its empty-state placeholder renders.
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
            trigger: "[data-menu-xmlid='pan_mcp_pro_governance.menu_mcp_governance_api_calls']",
            content: "Navigate to API Call Log",
            run: "click",
        },
        {
            trigger: ".o_view_nocontent_smiling_face",
            content: "API Call Log empty state visible",
        },
        {
            trigger: "[data-menu-xmlid='pan_mcp_pro_governance.menu_mcp_governance_identities']",
            content: "Navigate to Agent Identities",
            run: "click",
        },
        {
            trigger: ".o_view_nocontent_smiling_face",
            content: "Agent Identities empty state visible",
        },
    ],
});
