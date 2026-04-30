/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { dynamicApiRegistry } from "../../js/dynamic_api_registry";

/**
 * AddFieldDialog
 * ==============
 * Modal dialog for creating a new custom field on the target model.
 * Calls Python ``dynamic.api.field.create_field_on_model`` via RPC,
 * then notifies the parent via ``onFieldCreated`` so it can refresh
 * the FieldSelector list.
 *
 * Props
 * -----
 * endpointId  : int    — ID of the dynamic.api.endpoint record
 * modelId     : int    — ir.model.id for the target model
 * modelName   : str    — technical model name (for display only)
 * onFieldCreated : Function(newFieldData)  — parent callback
 * onClose        : Function()              — parent callback to close dialog
 */
export class AddFieldDialog extends Component {
    static template = "dynamic_rest_api.AddFieldDialog";
    static props = {
        endpointId: { type: Number },
        modelId: { type: Number },
        modelName: { type: String },
        onFieldCreated: { type: Function },
        onClose: { type: Function },
    };

    static FIELD_TYPES = [
        { value: 'char',     label: 'Text (Char)' },
        { value: 'text',     label: 'Long Text' },
        { value: 'integer',  label: 'Integer' },
        { value: 'float',    label: 'Float / Decimal' },
        { value: 'boolean',  label: 'Boolean (True/False)' },
        { value: 'date',     label: 'Date' },
        { value: 'datetime', label: 'Date & Time' },
        { value: 'selection',label: 'Selection (Dropdown)' },
    ];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            fieldLabel: '',
            fieldName: '',          // auto-generated, editable
            fieldNameManual: false, // user has manually edited the name
            fieldType: 'char',
            defaultValue: '',
            required: false,
            saving: false,
            errors: {},
        });
    }

    get fieldTypes() {
        return AddFieldDialog.FIELD_TYPES;
    }

    // ── Auto-slugify label → field name ───────────────────────────────

    _slugify(str) {
        return str
            .toLowerCase()
            .trim()
            .replace(/[\s\-]+/g, '_')
            .replace(/[^a-z0-9_]/g, '')
            .replace(/^_+|_+$/g, '');
    }

    onLabelInput(ev) {
        const label = ev.target.value;
        this.state.fieldLabel = label;
        if (!this.state.fieldNameManual) {
            this.state.fieldName = this._slugify(label);
        }
        this._validateField('fieldLabel', label);
    }

    onFieldNameInput(ev) {
        this.state.fieldName = ev.target.value;
        this.state.fieldNameManual = true;
        this._validateField('fieldName', ev.target.value);
    }

    onFieldTypeChange(ev) {
        this.state.fieldType = ev.target.value;
    }

    onDefaultValueInput(ev) {
        this.state.defaultValue = ev.target.value;
    }

    onRequiredToggle(ev) {
        this.state.required = ev.target.checked;
    }

    // ── Validation ────────────────────────────────────────────────────

    _validateField(field, value) {
        const errs = { ...this.state.errors };
        if (field === 'fieldLabel') {
            errs.fieldLabel = value.trim() ? null : 'Field label is required.';
        }
        if (field === 'fieldName') {
            const clean = value.trim();
            if (!clean) {
                errs.fieldName = 'Technical name is required.';
            } else if (!/^[a-z_][a-z0-9_]*$/.test(clean)) {
                errs.fieldName = 'Only lowercase letters, digits, underscores. Cannot start with a digit.';
            } else {
                errs.fieldName = null;
            }
        }
        this.state.errors = errs;
    }

    _validate() {
        this._validateField('fieldLabel', this.state.fieldLabel);
        this._validateField('fieldName', this.state.fieldName);
        return !Object.values(this.state.errors).some(Boolean);
    }

    get hasErrors() {
        return Object.values(this.state.errors).some(Boolean);
    }

    // ── Computed display ─────────────────────────────────────────────

    get previewName() {
        const base = this.state.fieldName.trim();
        return base ? `x_${base}` : 'x_…';
    }

    // ── Submit ────────────────────────────────────────────────────────

    async onConfirm() {
        if (!this._validate()) return;
        if (this.state.saving) return;

        this.state.saving = true;
        try {
            const result = await dynamicApiRegistry.createCustomField(
                this.orm,
                this.props.endpointId,
                {
                    field_label:   this.state.fieldLabel.trim(),
                    field_name:    this.state.fieldName.trim(),
                    field_type:    this.state.fieldType,
                    default_value: this.state.defaultValue.trim() || null,
                    required:      this.state.required,
                }
            );

            // Bust client field cache so FieldSelector will reload
            dynamicApiRegistry.bustFieldCache(this.props.modelId);

            this.notification.add(
                `Custom field "${result.name}" created successfully.`,
                { type: 'success' }
            );

            this.props.onFieldCreated(result);
            this.props.onClose();
        } catch (err) {
            const msg = err.data?.message || err.message || String(err);
            this.notification.add(`Failed to create field: ${msg}`, { type: 'danger' });
        } finally {
            this.state.saving = false;
        }
    }

    onCancel() {
        this.props.onClose();
    }
}
