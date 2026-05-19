// /** @odoo-module **/

// import { patch } from "@web/core/utils/patch";
// import { Composer } from "@mail/core/common/composer";

// patch(Composer.prototype, {

//     async sendMessage() {

//         const composer = this.props?.composer;

//         if (!composer) {
//             return;
//         }

//         const thread = composer.targetThread;

//         if (!thread) {
//             console.error("Missing targetThread");
//             return;
//         }

//         const body = composer.composerText;

//         if (!body || !body.trim()) {
//             return;
//         }

//         const replyService =
//             this.env.services.chatReply;

//         const parentId =
//             replyService?.replyMessage?.id || false;

//         await this.env.services.orm.call(
//             thread.model,
//             "message_post",
//             [thread.id],
//             {
//                 body: body,
//                 message_type: "comment",
//                 subtype_xmlid: "mail.mt_comment",
//                 parent_id: parentId,
//             }
//         );

//         composer.composerText = "";

//         if (replyService) {
//             replyService.replyMessage = null;
//         }
//     },

// });
/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer";

patch(Composer.prototype, {

    async sendMessage() {

        const composer = this.props.composer;

        if (!composer) {
            return;
        }

        const thread =
            composer.targetThread;

        if (!thread) {
            return;
        }

        const body =
            composer.composerText;

        if (!body || !body.trim()) {
            return;
        }

        const replyService =
            this.env.services.chatReply;

        const parentId =
            replyService.replyMessage?.id || false;

        await this.env.services.orm.call(
            thread.model,
            "message_post",
            [thread.id],
            {
                body: body,
                message_type: "comment",
                subtype_xmlid: "mail.mt_comment",
                parent_id: parentId,
            }
        );

        composer.composerText = "";

        replyService.replyMessage = null;
    },

});