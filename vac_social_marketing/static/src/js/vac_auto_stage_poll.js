/** @odoo-module **/

/**
 * VAC Auto Stage Poll Service
 * ─────────────────────────────────────────────────────────────────────────────
 * Polls every 10 seconds. If the user is currently viewing a Social (FB/ING)
 * or Event list / kanban / form, it calls the backend to check whether any
 * record's stage needs updating (Ongoing / Completed based on due-date).
 * When something changed the current view silently reloads so the user sees
 * the correct stage without any manual refresh.
 */

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

const VAC_MODELS = ["vac.social.fb", "vac.social.ing", "vac.event"];
const POLL_INTERVAL_MS = 10_000; // 10 seconds

export const vacAutoStagePollService = {
    dependencies: ["orm", "action"],

    async start(env, { orm, action }) {

        async function poll() {
            try {
                // Detect the model currently rendered in the view
                const ctrl = action.currentController;
                if (!ctrl) return;

                const resModel =
                    ctrl.model?.config?.resModel ||          // list / kanban / form (OWL)
                    ctrl.props?.resModel ||                   // fallback
                    null;

                if (!resModel || !VAC_MODELS.includes(resModel)) return;

                // Ask the backend to push any overdue records into Ongoing / Completed.
                // Returns true when at least one record was actually written.
                const changed = await orm.call(
                    resModel,
                    "action_auto_stage_poll",
                    [],
                    {}
                );

                if (changed) {
                    // Reload the view data in-place (preserves pagination / search)
                    if (ctrl.model?.load) {
                        await ctrl.model.load();
                        // Trigger OWL re-render on the root component
                        ctrl.component?.__owl__?.root?.render?.(true);
                    } else {
                        // Fallback: restore the full action (resets scroll but always works)
                        action.restore();
                    }
                }
            } catch (_e) {
                // Silently swallow – the user may be navigating, session expired, etc.
            }
        }

        // Kick off the first check after an initial delay so the page
        // has time to finish loading, then repeat every 10 s.
        browser.setTimeout(poll, 2000);
        browser.setInterval(poll, POLL_INTERVAL_MS);
    },
};

registry.category("services").add("vac_auto_stage_poll", vacAutoStagePollService);
