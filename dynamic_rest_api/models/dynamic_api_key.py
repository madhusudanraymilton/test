# -*- coding: utf-8 -*-
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DynamicApiKey(models.Model):
    """
    API Key for authenticating requests to dynamic endpoints.

    Security model:
    - The raw secret is generated once and returned to the user via a wizard.
    - Only a SHA-256 hash is persisted in the database.
    - The key_prefix (first 8 chars) is stored in plaintext for UI identification.
    - Comparison at request time: sha256(incoming_key) == stored key_hash.
    """
    _name = 'dynamic.api.key'
    _description = 'Dynamic REST API Key'
    _order = 'name'
    _rec_name = 'display_name'

    name = fields.Char(string='Key Name', required=True, help='Descriptive label for this key.')
    user_id = fields.Many2one(
        'res.users', string='Owner', required=True,
        default=lambda self: self.env.user,
        ondelete='cascade',
    )
    key_prefix = fields.Char(
        string='Key Prefix', readonly=True,
        help='First 8 characters of the key — for identification only.',
    )
    key_hash = fields.Char(
        string='Key Hash (SHA-256)', readonly=True,
        help='SHA-256 hash of the raw key. Never stored in plaintext.',
    )
    expiry_date = fields.Date(
        string='Expiry Date',
        help='Leave empty for a non-expiring key.',
    )
    is_active = fields.Boolean(string='Active', default=True)
    endpoint_ids = fields.Many2many(
        'dynamic.api.endpoint',
        'endpoint_api_key_rel', 'key_id', 'endpoint_id',
        string='Allowed Endpoints',
        help='If empty, the key is valid for all endpoints that accept API keys.',
    )
    last_used = fields.Datetime(string='Last Used', readonly=True)
    request_count = fields.Integer(string='Request Count', readonly=True, default=0)
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name', store=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Computed
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('name', 'key_prefix')
    def _compute_display_name(self):
        for rec in self:
            prefix = f' ({rec.key_prefix}...)' if rec.key_prefix else ''
            rec.display_name = f'{rec.name}{prefix}'

    # ─────────────────────────────────────────────────────────────────────────
    # Key generation & validation
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _generate_raw_key():
        """Generate a cryptographically secure 43-character URL-safe key."""
        return secrets.token_urlsafe(32)  # ~43 chars

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """Return SHA-256 hex digest of the raw key."""
        return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()

    @api.model
    def create_with_key(self, name, user_id=None, expiry_date=None, endpoint_ids=None):
        """
        Create a new API key record and return (record, raw_key).
        The raw_key is the only time the secret is available; callers must
        display it to the user immediately.
        """
        raw_key = self._generate_raw_key()
        key_hash = self._hash_key(raw_key)
        vals = {
            'name': name,
            'user_id': user_id or self.env.uid,
            'key_hash': key_hash,
            'key_prefix': raw_key[:8],
            'is_active': True,
        }
        if expiry_date:
            vals['expiry_date'] = expiry_date
        if endpoint_ids:
            vals['endpoint_ids'] = [(6, 0, endpoint_ids)]
        record = self.sudo().create(vals)
        return record, raw_key

    def action_generate_new_key(self):
        """
        Regenerate the key for an existing record.
        Opens the reveal wizard so the user can copy the new secret.
        """
        self.ensure_one()
        raw_key = self._generate_raw_key()
        self.sudo().write({
            'key_hash': self._hash_key(raw_key),
            'key_prefix': raw_key[:8],
        })
        return self.env['dynamic.api.key.reveal.wizard'].create({
            'api_key_id': self.id,
            'raw_key': raw_key,
        }).action_open_wizard()

    def action_create_and_reveal(self):
        """
        Button on the form: generate a key for an already-saved record
        that has no key_hash yet (e.g. created via form view).
        """
        self.ensure_one()
        if self.key_hash:
            raise UserError(_('A key has already been generated. Use "Regenerate" to replace it.'))
        return self.action_generate_new_key()

    # ─────────────────────────────────────────────────────────────────────────
    # Validation at request time (called by controller)
    # ─────────────────────────────────────────────────────────────────────────

    @api.model
    def validate_key(self, raw_key: str, endpoint=None):
        """
        Returns the matching DynamicApiKey record, or raises UserError.

        Parameters
        ----------
        raw_key  : str   The value from the X-API-Key header.
        endpoint : dynamic.api.endpoint recordset (optional)
                   If supplied, also checks endpoint membership.
        """
        if not raw_key:
            raise UserError(_('Missing X-API-Key header.'))

        key_hash = self._hash_key(raw_key)
        domain = [('key_hash', '=', key_hash), ('is_active', '=', True)]
        api_key = self.sudo().search(domain, limit=1)

        if not api_key:
            raise UserError(_('Invalid or revoked API key.'))

        # Check expiry
        if api_key.expiry_date and api_key.expiry_date < fields.Date.today():
            raise UserError(_('This API key has expired.'))

        # Check endpoint restriction
        if endpoint and api_key.endpoint_ids:
            if endpoint.id not in api_key.endpoint_ids.ids:
                raise UserError(_('This API key is not authorized for this endpoint.'))

        # Update usage stats (in a separate savepoint to not block the request)
        try:
            api_key.sudo().write({
                'last_used': fields.Datetime.now(),
                'request_count': api_key.request_count + 1,
            })
        except Exception:
            pass  # Do not fail the request if the stats update fails

        return api_key

    # ─────────────────────────────────────────────────────────────────────────
    # Rate limiting helper
    # ─────────────────────────────────────────────────────────────────────────

    def check_rate_limit(self, endpoint):
        """
        Simple per-key, per-minute rate limit using dynamic.api.log count.
        Returns True if within limit, False if exceeded.
        """
        limit = endpoint.rate_limit
        if not limit:
            return True  # 0 = unlimited

        since = datetime.utcnow() - timedelta(minutes=1)
        count = self.env['dynamic.api.log'].sudo().search_count([
            ('endpoint_id', '=', endpoint.id),
            ('api_key_id', '=', self.id),
            ('timestamp', '>=', fields.Datetime.to_string(since)),
        ])
        return count < limit
