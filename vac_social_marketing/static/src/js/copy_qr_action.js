/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * Client action: copy the QR code image (with record name label) to clipboard.
 * Params: qr_code (base64 PNG string), record_name (event/campaign title)
 */
async function copyQrWithName(env, action) {
    var params = action.params || {};
    var qr_code = params.qr_code || "";
    var record_name = params.record_name || "";

    if (!qr_code) {
        env.services.notification.add(_t("No QR code available yet."), {
            title: _t("Copy QR"),
            type: "warning",
        });
        return;
    }

    try {
        var img = new Image();
        await new Promise(function(resolve, reject) {
            img.onload = resolve;
            img.onerror = reject;
            img.src = "data:image/png;base64," + qr_code;
        });

        var padding = 16;
        var fontSize = 16;
        var lineHeight = fontSize + 8;

        var canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth + padding * 2;
        canvas.height = img.naturalHeight + lineHeight + padding * 2 + 4;

        var ctx = canvas.getContext("2d");

        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = "#1a1a2e";
        ctx.font = "bold " + fontSize + "px Arial, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillText(record_name, canvas.width / 2, padding);

        ctx.drawImage(img, padding, padding + lineHeight + 4);

        var blob = await new Promise(function(resolve) {
            canvas.toBlob(resolve, "image/png");
        });

        await navigator.clipboard.write([
            new ClipboardItem({ "image/png": blob })
        ]);

        env.services.notification.add(
            _t("QR code copied! Paste it anywhere (Word, WhatsApp, email)."),
            { title: _t("QR Copied"), type: "success" }
        );

    } catch (err) {
        console.warn("copyQrWithName clipboard error:", err);
        env.services.notification.add(
            _t("Could not copy automatically. Right-click the QR image and choose Copy image."),
            { title: _t("Copy QR"), type: "warning", sticky: true }
        );
    }
}

registry
    .category("actions")
    .add("vac_social_marketing.copy_qr_with_name", copyQrWithName);
