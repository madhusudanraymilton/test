# -*- coding: utf-8 -*-
import re
import logging
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class DynamicApiEndpoint(models.Model):
    """
    Central configuration record for a single REST API endpoint.

    Design: one endpoint ↔ one Odoo model.  The controller uses a single
    master route ``/api/dynamic/<path:endpoint_path>`` registered at boot time.
    At each request the controller performs a cached DB lookup here — so new
    endpoints become live the moment they are saved, with zero server restarts.
    """
    _name = 'dynamic.api.endpoint'
    _description = 'Dynamic REST API Endpoint'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    # ── Basic metadata ────────────────────────────────────────────────────────

    name = fields.Char(
        string='Endpoint Name', required=True, tracking=True,
        help='Human-readable label, e.g. "Sales Orders API"',
    )
    description = fields.Text(string='Description')

    # ── Target model ─────────────────────────────────────────────────────────

    model_id = fields.Many2one(
        'ir.model', string='Target Model', required=True,
        ondelete='cascade', tracking=True,
        domain=[('transient', '=', False)],
        help='The Odoo model whose records will be served by this endpoint.',
    )
    # Stored so the controller can use it without a join
    model_name = fields.Char(
        related='model_id.model', store=True, string='Model Technical Name',
    )
    model_display_name = fields.Char(
        related='model_id.name', store=True, string='Model Label',
    )

    # ── URL ───────────────────────────────────────────────────────────────────

    endpoint_path = fields.Char(
        string='Endpoint Path',
        compute='_compute_endpoint_path',
        store=True, readonly=True,
        help='Auto-generated URL, e.g. /api/dynamic/sale-order',
    )

    # ── HTTP methods (Boolean flags — simplest, most Odoo-native approach) ───

    allow_get = fields.Boolean(string='GET', default=True)
    allow_post = fields.Boolean(string='POST', default=False)
    allow_put = fields.Boolean(string='PUT', default=False)
    allow_delete = fields.Boolean(string='DELETE', default=False)

    # ── Field selection ───────────────────────────────────────────────────────

    field_ids = fields.One2many(
        'dynamic.api.field', 'endpoint_id', string='Exposed Fields',
    )
    allow_create_field = fields.Boolean(
        string='Allow Adding Custom Fields',
        help='When enabled, users may create new ir.model.fields on the target '
             'model directly from the Endpoint Builder UI.',
    )

    # ── Authentication ────────────────────────────────────────────────────────

    auth_type = fields.Selection(
        selection=[
            ('public',  'Public (No Authentication)'),
            ('api_key', 'API Key  (X-API-Key header)'),
            ('session', 'Odoo Session Cookie'),
        ],
        string='Authentication Type', default='api_key', required=True,
        tracking=True,
    )
    api_key_ids = fields.Many2many(
        'dynamic.api.key',
        'endpoint_api_key_rel', 'endpoint_id', 'key_id',
        string='Allowed API Keys',
        help='If empty and auth_type=api_key, any valid active key is accepted.',
    )

    # ── State ─────────────────────────────────────────────────────────────────

    is_active = fields.Boolean(string='Active', default=True, tracking=True)

    # ── CORS / rate limiting ──────────────────────────────────────────────────

    cors_origins = fields.Char(
        string='CORS Origins', default='*',
        help='Comma-separated list of allowed origins, or * for all.',
    )
    rate_limit = fields.Integer(
        string='Rate Limit (req/min)', default=60,
        help='Maximum requests per minute per API key (0 = unlimited).',
    )

    # ── Computed stats (no store — live from log table) ───────────────────────

    request_count = fields.Integer(
        string='Total Requests', compute='_compute_stats',
    )
    last_called = fields.Datetime(
        string='Last Called', compute='_compute_stats',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Computed fields
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('model_name')
    def _compute_endpoint_path(self):
        for rec in self:
            if rec.model_name:
                # Replace dots with hyphens, lower-case → URL-safe slug
                slug = re.sub(r'[^a-z0-9\-]', '-', rec.model_name.lower())
                slug = re.sub(r'-{2,}', '-', slug).strip('-')
                rec.endpoint_path = f'/api/dynamic/{slug}'
            else:
                rec.endpoint_path = False

    def _compute_stats(self):
        Log = self.env['dynamic.api.log']
        for rec in self:
            logs = Log.search([('endpoint_id', '=', rec.id)])
            rec.request_count = len(logs)
            rec.last_called = max(logs.mapped('timestamp')) if logs else False

    # ─────────────────────────────────────────────────────────────────────────
    # Cache management
    # ─────────────────────────────────────────────────────────────────────────

    @api.model
    @tools.ormcache('endpoint_path')
    def _get_cached_endpoint_id(self, endpoint_path):
        """
        Low-level cached lookup: path → endpoint record ID (int or False).

        Why ormcache here:
          ormcache stores results per (database, *args).  The controller calls
          this on every request.  Because we cache only the ID (an integer),
          the cache footprint is tiny.  Cache is explicitly busted via
          _invalidate_endpoint_cache() on every write/create/unlink.

        This is the "registry lookup at request time" pattern: the route is
        registered once at boot, but the routing table (which model, which
        fields, which methods) lives in the database and is fetched on-demand.
        """
        endpoint = self.sudo().search(
            [('endpoint_path', '=', endpoint_path), ('is_active', '=', True)],
            limit=1,
        )
        return endpoint.id if endpoint else False

    def _invalidate_endpoint_cache(self):
        """Bust the ormcache so the next request re-reads from DB."""
        self.env['dynamic.api.endpoint']._get_cached_endpoint_id.clear_cache(
            self.env['dynamic.api.endpoint']
        )

    @api.model
    def _get_endpoint_for_request(self, path):
        """
        Used by the controller: returns a live recordset (may be empty).
        The two-step approach (cached ID → fresh browse) avoids stale ORM
        objects while still benefiting from the cache.
        """
        endpoint_id = self._get_cached_endpoint_id(path)
        if not endpoint_id:
            return self.browse()
        return self.browse(endpoint_id).sudo().exists()

    # ─────────────────────────────────────────────────────────────────────────
    # ORM overrides — keep cache consistent
    # ─────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._invalidate_endpoint_cache()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._invalidate_endpoint_cache()
        return result

    def unlink(self):
        self._invalidate_endpoint_cache()
        return super().unlink()

    # ─────────────────────────────────────────────────────────────────────────
    # Constraints
    # ─────────────────────────────────────────────────────────────────────────

    @api.constrains('model_id')
    def _check_unique_model(self):
        for rec in self:
            if not rec.model_id:
                continue
            duplicate = self.search([
                ('model_id', '=', rec.model_id.id),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'An endpoint for model "%(model)s" already exists: %(name)s',
                    model=rec.model_name, name=duplicate.name,
                ))

    @api.constrains('allow_get', 'allow_post', 'allow_put', 'allow_delete')
    def _check_at_least_one_method(self):
        for rec in self:
            if not any([rec.allow_get, rec.allow_post, rec.allow_put, rec.allow_delete]):
                raise ValidationError(_('At least one HTTP method must be enabled.'))

    # ─────────────────────────────────────────────────────────────────────────
    # Action buttons
    # ─────────────────────────────────────────────────────────────────────────

    def action_activate(self):
        self.ensure_one()
        self.write({'is_active': True})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_deactivate(self):
        self.ensure_one()
        self.write({'is_active': False})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_builder(self):
        """Open the OWL-based EndpointBuilder client action."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'dynamic_rest_api.endpoint_builder',
            'name': _('Endpoint Builder — %s') % self.name,
            'params': {'endpoint_id': self.id},
            'target': 'current',
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Logs — %s') % self.name,
            'res_model': 'dynamic.api.log',
            'view_mode': 'list,form',
            'domain': [('endpoint_id', '=', self.id)],
            'context': {'default_endpoint_id': self.id},
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Helper methods used by the controller
    # ─────────────────────────────────────────────────────────────────────────

    def get_allowed_methods(self):
        """Returns list like ['GET', 'POST'] for this endpoint."""
        methods = []
        if self.allow_get:    methods.append('GET')
        if self.allow_post:   methods.append('POST')
        if self.allow_put:    methods.append('PUT')
        if self.allow_delete: methods.append('DELETE')
        return methods

    def get_readable_field_names(self):
        """Field names exposed for GET responses."""
        return [f.field_name for f in self.field_ids if f.field_id and f.field_name]

    def get_writable_field_names(self):
        """Field names allowed in POST/PUT bodies."""
        return [
            f.field_name for f in self.field_ids
            if f.field_id and f.field_name and not f.is_readonly
        ]

    def get_field_alias_map(self):
        """Returns {field_name: alias_or_field_name} for JSON key renaming."""
        return {
            f.field_name: (f.alias.strip() if f.alias else f.field_name)
            for f in self.field_ids
            if f.field_id and f.field_name
        }

    def get_reverse_alias_map(self):
        """Returns {alias: field_name} for deserialising incoming POST/PUT bodies."""
        return {
            (f.alias.strip() if f.alias else f.field_name): f.field_name
            for f in self.field_ids
            if f.field_id and f.field_name and not f.is_readonly
        }
