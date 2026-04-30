/** @odoo-module **/
import { Component, useState, useEffect } from "@odoo/owl";

/**
 * FieldSelector
 * =============
 * Displays all fields of a chosen ir.model as a filterable, selectable list.
 * Emits ``field-toggled`` when the user checks/unchecks a field.
 * Emits ``alias-changed`` when the user edits an alias inline.
 *
 * Props
 * -----
 * availableFields : Array  — from dynamicApiRegistry.fetchModelFields()
 * selectedLines   : Array  — [{field_id, alias, is_readonly, sequence}, ...]
 * readonly        : bool
 */
export class FieldSelector extends Component {
    static template = "dynamic_rest_api.FieldSelector";
    static props = {
        availableFields: { type: Array },
        selectedLines: { type: Array },
        readonly: { type: Boolean, optional: true, default: false },
        onFieldToggled: { type: Function },
        onAliasChanged: { type: Function },
        onReadonlyChanged: { type: Function },
    };

    setup() {
        this.state = useState({
            filter: '',
            groupBy: 'none',   // 'none' | 'ttype'
        });
    }

    // ── Derived data ───────────────────────────────────────────────────

    get filteredFields() {
        const q = this.state.filter.trim().toLowerCase();
        return this.props.availableFields.filter(f => {
            if (!q) return true;
            return (
                f.name.toLowerCase().includes(q) ||
                f.field_description.toLowerCase().includes(q) ||
                f.ttype.toLowerCase().includes(q)
            );
        });
    }

    get groupedFields() {
        if (this.state.groupBy !== 'ttype') {
            return [{ label: null, fields: this.filteredFields }];
        }
        const groups = {};
        for (const f of this.filteredFields) {
            (groups[f.ttype] = groups[f.ttype] || []).push(f);
        }
        return Object.entries(groups)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([label, fields]) => ({ label, fields }));
    }

    isSelected(fieldId) {
        return this.props.selectedLines.some(l => l.field_id === fieldId);
    }

    getLineForField(fieldId) {
        return this.props.selectedLines.find(l => l.field_id === fieldId);
    }

    getAlias(fieldId) {
        return this.getLineForField(fieldId)?.alias || '';
    }

    getIsReadonly(fieldId) {
        return !!this.getLineForField(fieldId)?.is_readonly;
    }

    // ── Handlers ──────────────────────────────────────────────────────

    onToggle(field) {
        this.props.onFieldToggled(field);
    }

    onAliasInput(field, ev) {
        this.props.onAliasChanged(field.id, ev.target.value);
    }

    onReadonlyToggle(field, ev) {
        this.props.onReadonlyChanged(field.id, ev.target.checked);
    }

    onFilterInput(ev) {
        this.state.filter = ev.target.value;
    }

    onGroupByChange(ev) {
        this.state.groupBy = ev.target.value;
    }

    get selectedCount() {
        return this.props.selectedLines.length;
    }

    get totalCount() {
        return this.props.availableFields.length;
    }
}
