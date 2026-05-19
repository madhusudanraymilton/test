/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Message } from "@mail/core/common/message";

patch(Message.prototype, {

    computeActions() {

        const result =
            super.computeActions(...arguments);

        if (!this.messageActions) {
            return result;
        }

        this.messageActions.actions =
            this.messageActions.actions.filter(
                (action) => action.id !== "reply"
            );

        return result;
    },

});