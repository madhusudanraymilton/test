/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

async function copyRegistrationLink(env, action) {
    const link = action.params?.link || "";
    if (!link) {
        env.services.notification.add(_t("No registration link found."), {
            title: _t("Copy Link"),
            type: "warning",
        });
        return;
    }

    try {
        await browser.navigator.clipboard.writeText(link);
        env.services.notification.add(_t("Registration link copied."), {
            title: _t("Copy Link"),
            type: "success",
        });
    } catch {
        env.services.notification.add(link, {
            title: _t("Could not copy automatically"),
            type: "warning",
            sticky: true,
        });
    }
}

registry.category("actions").add("vac_social_marketing.copy_registration_link", copyRegistrationLink);
