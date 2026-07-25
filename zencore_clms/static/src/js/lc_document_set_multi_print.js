/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Client action: "LC Document Set" (multi report download)
 * ──────────────────────────────────────────────────────────
 * Triggered from the invoice Print menu (see account_move_extended.py ::
 * action_download_lc_document_set). Instead of opening one merged PDF,
 * this downloads the 4 underlying LC documents one after another:
 *   1. Delivery Challan
 *   2. Commercial Invoice
 *   3. Certificate of Origin
 *   4. Beneficiary Certificate
 *
 * A short delay is used between downloads so the browser treats each
 * one as a distinct, user-triggered download instead of collapsing/
 * blocking rapid back-to-back file saves.
 */
async function downloadLcDocumentSet(env, action) {
    const reportActions = (action.params && action.params.report_actions) || [];

    for (const reportAction of reportActions) {
        await env.services.action.doAction(reportAction);
        // eslint-disable-next-line no-await-in-loop
        await new Promise((resolve) => setTimeout(resolve, 900));
    }

    return { type: "ir.actions.act_window_close" };
}

registry.category("actions").add("zencore_clms_multi_report_download", downloadLcDocumentSet);
