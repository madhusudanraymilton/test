// /** @odoo-module **/

// import { registerMessageAction } from "@mail/core/common/message_actions";
// import { _t } from "@web/core/l10n/translation";

// registerMessageAction("zencore-reply", {

//     condition: ({ message }) => {
//         return (
//             message &&
//             message.message_type === "comment"
//         );
//     },

//     icon: "fa fa-reply",

//     title: () => _t("Reply"),

//     sequence: 20,

//     onSelected: ({ message, owner }) => {

//         const chatReply =
//             owner.env.services.chatReply;

//         if (!chatReply) {
//             console.error("chatReply service missing");
//             return;
//         }

//         chatReply.replyMessage = {
//             id: message.id,
//             body: message.inlineBody,
//             authorName: message.authorName,
//         };

//         console.log("Reply selected:", message.id);
//     },
// });
/** @odoo-module **/

import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("zencore_reply", {

    condition: ({ message }) => {

        return (
            message &&
            message.message_type === "comment" &&
            !message.isSelfAuthored
        );
    },

    icon: "fa fa-reply",

    title: () => _t("Reply"),

    sequence: 100,

    onSelected: ({ message, owner }) => {

        const replyService =
            owner.env.services.chatReply;

        replyService.replyMessage = {
            id: message.id,
            body: message.inlineBody,
            authorName: message.authorName,
        };

        /*
        Activate Send Message tab automatically
        */
        const chatter =
            owner.props.thread?.composer;

        if (chatter) {
            chatter.type = "comment";
        }
    },
});