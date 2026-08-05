/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export class NoSearchMoreMany2OneField extends Many2OneField {
    get Many2XAutocompleteProps() {
        return {
            ...super.Many2XAutocompleteProps,
            noSearchMore: true,
        };
    }
}

export const noSearchMoreMany2OneField = {
    ...many2OneField,
    component: NoSearchMoreMany2OneField,
};

registry.category("fields").add("vac_no_search_more_many2one", noSearchMoreMany2OneField);
