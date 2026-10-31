/** @odoo-module **/

/**
 * Brightloop Subscription Management – Backend Web Client UI Helper
 * Enhances dashboard KPI cards, smooth transitions, and numerical formatting.
 */

import { registry } from "@web/core/registry";

export const BrightloopDashboardService = {
    start() {
        // Log initialization
        console.log("[Brightloop Subscriptions] Backend UI assets and KPI card styles loaded.");
    }
};

registry.category("services").add("brightloop_dashboard_service", BrightloopDashboardService);
