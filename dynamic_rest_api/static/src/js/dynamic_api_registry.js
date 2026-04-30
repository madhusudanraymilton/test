/** @odoo-module **/
/**
 * dynamic_api_registry.js
 *
 * Thin client-side helper that wraps ORM calls for the EndpointBuilder
 * components.  Keeps a session-scoped cache of the last-loaded endpoint
 * data to reduce redundant RPC round-trips during a single editing session.
 *
 * This is NOT a persistence layer — all state lives server-side.
 * Think of it as a typed API client with a single-session memoisation layer.
 */

const _cache = new Map();

export const dynamicApiRegistry = {
    /**
     * Fetch all ir.model records (non-transient) for the model selector.
     * Result is cached for the session lifetime.
     */
    async fetchModels(orm) {
        if (_cache.has('models')) return _cache.get('models');
        const models = await orm.searchRead(
            'ir.model',
            [['transient', '=', false]],
            ['id', 'name', 'model'],
            { order: 'name asc', limit: 0 }
        );
        _cache.set('models', models);
        return models;
    },

    /**
     * Fetch all fields for a given ir.model.  Excludes Many2many / One2many
     * join fields and magic fields not useful for REST exposure.
     */
    async fetchModelFields(orm, modelId) {
        const cacheKey = `fields_${modelId}`;
        if (_cache.has(cacheKey)) return _cache.get(cacheKey);

        const EXCLUDE_TTYPES = ['one2many', 'reference'];
        const fields = await orm.searchRead(
            'ir.model.fields',
            [
                ['model_id', '=', modelId],
                ['ttype', 'not in', EXCLUDE_TTYPES],
                ['name', 'not in', [
                    '__last_update', 'message_ids', 'message_follower_ids',
                    'activity_ids', 'message_partner_ids',
                ]],
            ],
            ['id', 'name', 'field_description', 'ttype', 'required', 'store'],
            { order: 'field_description asc', limit: 0 }
        );
        _cache.set(cacheKey, fields);
        return fields;
    },

    /**
     * Load a full endpoint record with its field_ids expanded.
     */
    async fetchEndpoint(orm, endpointId) {
        const [ep] = await orm.read(
            'dynamic.api.endpoint',
            [endpointId],
            [
                'id', 'name', 'model_id', 'model_name', 'endpoint_path',
                'allow_get', 'allow_post', 'allow_put', 'allow_delete',
                'auth_type', 'is_active', 'allow_create_field',
                'cors_origins', 'rate_limit', 'description', 'field_ids',
            ]
        );
        // Expand field records
        if (ep.field_ids && ep.field_ids.length) {
            ep.fields = await orm.read(
                'dynamic.api.field',
                ep.field_ids,
                ['id', 'field_id', 'field_name', 'field_string',
                 'field_type', 'alias', 'is_readonly', 'is_custom', 'sequence']
            );
        } else {
            ep.fields = [];
        }
        return ep;
    },

    /**
     * Create a new custom field on the target model via Python RPC.
     */
    async createCustomField(orm, endpointId, fieldVals) {
        return orm.call(
            'dynamic.api.field',
            'create_field_on_model',
            [endpointId, fieldVals]
        );
    },

    /**
     * Save endpoint + field selection in one pass.
     * If endpointId is falsy, creates a new record.
     */
    async saveEndpoint(orm, endpointId, vals, fieldLines) {
        // Build field_ids commands
        const fieldCommands = fieldLines.map(line => {
            if (line.id) {
                // Update existing
                return [1, line.id, {
                    alias: line.alias || false,
                    is_readonly: line.is_readonly || false,
                    sequence: line.sequence || 10,
                }];
            } else {
                // Create new
                return [0, 0, {
                    field_id: line.field_id,
                    alias: line.alias || false,
                    is_readonly: line.is_readonly || false,
                    sequence: line.sequence || 10,
                }];
            }
        });

        // Delete lines not in fieldLines
        if (endpointId) {
            const existingIds = fieldLines.filter(l => l.id).map(l => l.id);
            const currentFields = await orm.read(
                'dynamic.api.endpoint', [endpointId], ['field_ids']
            );
            const toDelete = (currentFields[0]?.field_ids || [])
                .filter(id => !existingIds.includes(id));
            toDelete.forEach(id => fieldCommands.push([2, id]));
        }

        const writeVals = { ...vals, field_ids: fieldCommands };

        if (endpointId) {
            await orm.write('dynamic.api.endpoint', [endpointId], writeVals);
            return endpointId;
        } else {
            const newId = await orm.create('dynamic.api.endpoint', [writeVals]);
            return newId;
        }
    },

    /** Bust the session field cache for a model (after adding custom fields). */
    bustFieldCache(modelId) {
        _cache.delete(`fields_${modelId}`);
    },

    /** Clear everything. */
    clearAll() {
        _cache.clear();
    },

    /** Build the base URL for an endpoint from the current window location. */
    getEndpointUrl(endpointPath) {
        const base = `${window.location.protocol}//${window.location.host}`;
        return `${base}${endpointPath}`;
    },
};
