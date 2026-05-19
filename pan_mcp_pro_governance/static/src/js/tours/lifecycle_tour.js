/** @odoo-module */

import { registry } from "@web/core/registry";

/**
 * Lifecycle tour for mcp.governance.agent.identity.
 *
 * Drives the full state machine through the UI:
 *   draft → active → suspended → active → revoked
 *
 * Verifies progressive disclosure of the header buttons along the way:
 * each transition button must only be visible in the states where it
 * makes sense. See docs/design.md.
 *
 * Driven from tests/test_lifecycle_tour.py via HttpCase.start_tour().
 */
registry.category("web_tour.tours").add("pan_mcp_pro_governance.lifecycle", {
    test: true,
    // The Agent Identities menu is hidden from end users (staged for a
    // future release), so this tour navigates straight to the action URL
    // instead of clicking through the menu.
    url: "/odoo/action-pan_mcp_pro_governance.action_mcp_governance_agent_identity",
    steps: () => [
        {
            trigger: ".o_list_button_add, button.o_list_button_add",
            content: "Click 'New' to create an agent",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_field_widget[name='name'] input",
            content: "Fill in the agent name",
            run: "edit Lifecycle Tour Bot",
        },
        // Persist — the list_button_save is the form's save button in
        // breadcrumb mode. Falls back to ctrl+s if not present.
        {
            trigger: ".o_form_button_save, .o_form_status_indicator_buttons .fa-cloud-upload",
            content: "Save the new agent",
            run: "click",
        },
        // Draft: Activate visible, Suspend NOT visible.
        {
            trigger: ".o_arrow_button_current:contains('Draft'), .o_statusbar_status [data-value='draft'].o_arrow_button_current",
            content: "Statusbar shows Draft",
        },
        {
            trigger: "button[name='action_activate']:visible",
            content: "Activate button is visible in draft",
            run: "click",
        },
        // Active: Suspend visible, Revoke visible, Activate NOT visible.
        {
            trigger: ".o_arrow_button_current:contains('Active'), .o_statusbar_status [data-value='active'].o_arrow_button_current",
            content: "Statusbar shows Active",
        },
        {
            trigger: "button[name='action_suspend']:visible",
            content: "Suspend button is visible in active",
            run: "click",
        },
        // Suspended: Activate visible again, Suspend NOT visible.
        {
            trigger: ".o_arrow_button_current:contains('Suspended'), .o_statusbar_status [data-value='suspended'].o_arrow_button_current",
            content: "Statusbar shows Suspended",
        },
        {
            trigger: "button[name='action_activate']:visible",
            content: "Activate button is visible again in suspended",
            run: "click",
        },
        // Re-active, then revoke (which triggers a confirm dialog).
        {
            trigger: ".o_arrow_button_current:contains('Active'), .o_statusbar_status [data-value='active'].o_arrow_button_current",
            content: "Back to Active",
        },
        {
            trigger: "button[name='action_revoke']:visible",
            content: "Revoke button visible",
            run: "click",
        },
        {
            trigger: ".modal-dialog .modal-footer button.btn-primary",
            content: "Confirm the revoke dialog",
            run: "click",
        },
        // Revoked: all transition buttons hidden.
        {
            trigger: ".o_arrow_button_current:contains('Revoked'), .o_statusbar_status [data-value='revoked'].o_arrow_button_current",
            content: "Statusbar shows Revoked",
        },
        {
            trigger: ".o_form_view:not(:has(button[name='action_activate']:visible)):not(:has(button[name='action_suspend']:visible)):not(:has(button[name='action_revoke']:visible))",
            content: "No transition buttons visible in revoked state",
        },
    ],
});
