/** @odoo-module **/
import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FieldSelector } from "../FieldSelector/FieldSelector";
import { AddFieldDialog } from "../AddFieldDialog/AddFieldDialog";
import { EndpointPreview } from "../EndpointPreview/EndpointPreview";
import { dynamicApiRegistry } from "../../js/dynamic_api_registry";

/**
 * EndpointBuilder
 * ===============
 * The main orchestrator component.  Registered as a client action
 * (tag: ``dynamic_rest_api.endpoint_builder``) and rendered when the user
 * clicks "Open Endpoint Builder" from the endpoint form view.
 *
 * Responsible for:
 *  - Loading models list for the model selector
 *  - Loading fields when a model is chosen
 *  - Managing the selectedLines array (field selection state)
 *  - Delegating field creation to AddFieldDialog
 *  - Showing live preview via EndpointPreview
 *  - Saving via dynamicApiRegistry.saveEndpoint()
 *
 * Props (from ir.actions.client params):
 *  endpoint_id : int | undefined
 */
export class EndpointBuilder extends Component {
    static template = "dynamic_rest_api.EndpointBuilder";
    static components = { FieldSelector, AddFieldDialog, EndpointPreview };
    static props = {
        // Passed by Odoo action framework as action.params
        action: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            // ── Loading flags ─────────────────────────────────────────
            loadingModels:  true,
            loadingFields:  false,
            saving:         false,

            // ── Data ──────────────────────────────────────────────────
            models:         [],   // [{id, name, model}]
            availableFields: [],  // ir.model.fields for selected model
            selectedLines:  [],   // [{field_id, field_name, alias, is_readonly,
                                  //   field_type, sequence, id?}]

            // ── Form values ───────────────────────────────────────────
            endpointId:     null,
            name:           '',
            modelId:        null,
            modelName:      '',
            modelLabel:     '',
            endpointPath:   '',
            allow_get:      true,
            allow_post:     false,
            allow_put:      false,
            allow_delete:   false,
            authType:       'api_key',
            allowCreateField: false,
            corsOrigins:    '*',
            rateLimit:      60,
            description:    '',
            isActive:       true,

            // ── UI state ──────────────────────────────────────────────
            showAddFieldDialog: false,
            modelSearchQuery:   '',
            dirty:              false,   // unsaved changes
        });

        onWillStart(async () => {
            await this._loadModels();
            const endpointId = this.props.action?.params?.endpoint_id;
            if (endpointId) {
                await this._loadEndpoint(endpointId);
            }
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Data loading
    // ─────────────────────────────────────────────────────────────────────────

    async _loadModels() {
        this.state.loadingModels = true;
        try {
            this.state.models = await dynamicApiRegistry.fetchModels(this.orm);
        } catch (err) {
            this.notification.add('Failed to load models: ' + err.message, { type: 'danger' });
        } finally {
            this.state.loadingModels = false;
        }
    }

    async _loadFieldsForModel(modelId) {
        this.state.loadingFields = true;
        this.state.availableFields = [];
        try {
            this.state.availableFields = await dynamicApiRegistry.fetchModelFields(
                this.orm, modelId
            );
        } catch (err) {
            this.notification.add('Failed to load fields: ' + err.message, { type: 'danger' });
        } finally {
            this.state.loadingFields = false;
        }
    }

    async _loadEndpoint(endpointId) {
        try {
            const ep = await dynamicApiRegistry.fetchEndpoint(this.orm, endpointId);
            // Populate form state from the existing endpoint
            this.state.endpointId    = ep.id;
            this.state.name          = ep.name;
            this.state.modelId       = ep.model_id[0];
            this.state.modelLabel    = ep.model_id[1];
            this.state.modelName     = ep.model_name;
            this.state.endpointPath  = ep.endpoint_path;
            this.state.allow_get     = ep.allow_get;
            this.state.allow_post    = ep.allow_post;
            this.state.allow_put     = ep.allow_put;
            this.state.allow_delete  = ep.allow_delete;
            this.state.authType      = ep.auth_type;
            this.state.allowCreateField = ep.allow_create_field;
            this.state.corsOrigins   = ep.cors_origins;
            this.state.rateLimit     = ep.rate_limit;
            this.state.description   = ep.description;
            this.state.isActive      = ep.is_active;

            // Load fields for the model
            await this._loadFieldsForModel(ep.model_id[0]);

            // Build selectedLines from existing field records
            this.state.selectedLines = ep.fields.map(f => ({
                id:         f.id,
                field_id:   f.field_id[0],
                field_name: f.field_name,
                field_type: f.field_type,
                alias:      f.alias || '',
                is_readonly: f.is_readonly,
                sequence:   f.sequence,
            }));
        } catch (err) {
            this.notification.add('Failed to load endpoint: ' + err.message, { type: 'danger' });
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Model selector
    // ─────────────────────────────────────────────────────────────────────────

    get filteredModels() {
        const q = this.state.modelSearchQuery.trim().toLowerCase();
        if (!q) return this.state.models;
        return this.state.models.filter(m =>
            m.name.toLowerCase().includes(q) || m.model.toLowerCase().includes(q)
        );
    }

    async onModelSelect(ev) {
        const modelId = parseInt(ev.target.value, 10);
        if (!modelId || modelId === this.state.modelId) return;

        const model = this.state.models.find(m => m.id === modelId);
        if (!model) return;

        this.state.modelId    = modelId;
        this.state.modelLabel = model.name;
        this.state.modelName  = model.model;
        this.state.endpointPath = this._buildPath(model.model);
        this.state.selectedLines = [];
        this.state.dirty = true;

        await this._loadFieldsForModel(modelId);
    }

    _buildPath(modelTechnicalName) {
        const slug = modelTechnicalName
            .toLowerCase()
            .replace(/[^a-z0-9\-]/g, '-')
            .replace(/-{2,}/g, '-')
            .replace(/^-|-$/g, '');
        return `/api/dynamic/${slug}`;
    }

    onModelSearch(ev) {
        this.state.modelSearchQuery = ev.target.value;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Field selection handlers (FieldSelector callbacks)
    // ─────────────────────────────────────────────────────────────────────────

    onFieldToggled(field) {
        const idx = this.state.selectedLines.findIndex(l => l.field_id === field.id);
        if (idx >= 0) {
            // Deselect
            this.state.selectedLines.splice(idx, 1);
        } else {
            // Select
            this.state.selectedLines.push({
                field_id:   field.id,
                field_name: field.name,
                field_type: field.ttype,
                alias:      '',
                is_readonly: false,
                sequence:   (this.state.selectedLines.length + 1) * 10,
            });
        }
        this.state.dirty = true;
    }

    onAliasChanged(fieldId, alias) {
        const line = this.state.selectedLines.find(l => l.field_id === fieldId);
        if (line) { line.alias = alias; this.state.dirty = true; }
    }

    onReadonlyChanged(fieldId, value) {
        const line = this.state.selectedLines.find(l => l.field_id === fieldId);
        if (line) { line.is_readonly = value; this.state.dirty = true; }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Form field handlers
    // ─────────────────────────────────────────────────────────────────────────

    onNameInput(ev)        { this.state.name = ev.target.value; this.state.dirty = true; }
    onAuthTypeChange(ev)   { this.state.authType = ev.target.value; this.state.dirty = true; }
    onCorsInput(ev)        { this.state.corsOrigins = ev.target.value; this.state.dirty = true; }
    onRateLimitInput(ev)   { this.state.rateLimit = parseInt(ev.target.value) || 0; this.state.dirty = true; }
    onDescriptionInput(ev) { this.state.description = ev.target.value; this.state.dirty = true; }

    onMethodToggle(method) {
        this.state[`allow_${method.toLowerCase()}`] = !this.state[`allow_${method.toLowerCase()}`];
        this.state.dirty = true;
    }

    onAllowCreateFieldToggle(ev) {
        this.state.allowCreateField = ev.target.checked;
        this.state.dirty = true;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // AddFieldDialog
    // ─────────────────────────────────────────────────────────────────────────

    openAddFieldDialog() {
        this.state.showAddFieldDialog = true;
    }

    closeAddFieldDialog() {
        this.state.showAddFieldDialog = false;
    }

    async onFieldCreated(newFieldData) {
        // Reload fields for the model to include the new one
        if (this.state.modelId) {
            await this._loadFieldsForModel(this.state.modelId);
        }
        // Auto-select the newly created field
        this.state.selectedLines.push({
            field_id:   newFieldData.id,
            field_name: newFieldData.name,
            field_type: newFieldData.ttype,
            alias:      '',
            is_readonly: false,
            sequence:   (this.state.selectedLines.length + 1) * 10,
            is_custom:  true,
        });
        this.state.dirty = true;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Save
    // ─────────────────────────────────────────────────────────────────────────

    async onSave() {
        if (this.state.saving) return;

        // Client-side validation
        if (!this.state.name.trim()) {
            this.notification.add('Please enter an endpoint name.', { type: 'warning' });
            return;
        }
        if (!this.state.modelId) {
            this.notification.add('Please select a target model.', { type: 'warning' });
            return;
        }
        const hasMethods = this.state.allow_get || this.state.allow_post
                        || this.state.allow_put  || this.state.allow_delete;
        if (!hasMethods) {
            this.notification.add('Enable at least one HTTP method.', { type: 'warning' });
            return;
        }

        this.state.saving = true;
        try {
            const vals = {
                name:               this.state.name.trim(),
                model_id:           this.state.modelId,
                allow_get:          this.state.allow_get,
                allow_post:         this.state.allow_post,
                allow_put:          this.state.allow_put,
                allow_delete:       this.state.allow_delete,
                auth_type:          this.state.authType,
                allow_create_field: this.state.allowCreateField,
                cors_origins:       this.state.corsOrigins,
                rate_limit:         this.state.rateLimit,
                description:        this.state.description,
                is_active:          this.state.isActive,
            };

            const savedId = await dynamicApiRegistry.saveEndpoint(
                this.orm,
                this.state.endpointId,
                vals,
                this.state.selectedLines,
            );

            this.state.endpointId = savedId;
            this.state.dirty = false;

            this.notification.add('Endpoint saved successfully!', { type: 'success' });

            // Reload so computed fields (endpoint_path) are fresh
            await this._loadEndpoint(savedId);

        } catch (err) {
            const msg = err.data?.message || err.message || String(err);
            this.notification.add(`Save failed: ${msg}`, { type: 'danger' });
        } finally {
            this.state.saving = false;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Navigation
    // ─────────────────────────────────────────────────────────────────────────

    onBack() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'API Endpoints',
            res_model: 'dynamic.api.endpoint',
            view_mode: 'list,form',
        });
    }

    openEndpointForm() {
        if (!this.state.endpointId) return;
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'dynamic.api.endpoint',
            res_id: this.state.endpointId,
            view_mode: 'form',
            views: [[false, 'form']],
        });
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Preview props helpers
    // ─────────────────────────────────────────────────────────────────────────

    get previewMethods() {
        return {
            allow_get:    this.state.allow_get,
            allow_post:   this.state.allow_post,
            allow_put:    this.state.allow_put,
            allow_delete: this.state.allow_delete,
        };
    }

    get previewSelectedFields() {
        // Enrich selectedLines with field_type for the preview
        return this.state.selectedLines.map(l => ({
            field_name: l.field_name,
            alias:      l.alias,
            is_readonly: l.is_readonly,
            field_type: l.field_type || 'char',
        }));
    }
}

// Register as a client action so ir.actions.client tag works
registry.category("actions").add("dynamic_rest_api.endpoint_builder", EndpointBuilder);
