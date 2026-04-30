# -*- coding: utf-8 -*-
import re
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DynamicApiField(models.Model):
    """
    One row per field exposed by a dynamic.api.endpoint.

    Each row points to an ir.model.fields record on the target model.
    The ``is_custom`` flag marks fields that were created by this module via
    ``create_field_on_model()``; those fields are deleted when the endpoint is
    unlinked if ``is_custom=True``.
    """
    _name = 'dynamic.api.field'
    _description = 'Dynamic API Exposed Field'
    _order = 'sequence, id'

    endpoint_id = fields.Many2one(
        'dynamic.api.endpoint', string='Endpoint',
        required=True, ondelete='cascade', index=True,
    )
    field_id = fields.Many2one(
        'ir.model.fields', string='Model Field',
        required=True, ondelete='cascade',
        domain="[('model_id', '=', parent.model_id)]",
    )
    # NOTE: Intentionally computed (not `related=`) because Odoo 19 enforces
    # strict type matching on related fields.  ir.model.fields.ttype is a
    # Selection field; declaring fields.Char(related='field_id.ttype') raises:
    #   TypeError: Type of related field … is inconsistent with ir.model.fields.ttype
    # A compute that stores a Char avoids the mismatch while keeping the
    # column stored and queryable.

    field_name = fields.Char(
        string='Technical Name', store=True,
        compute='_compute_field_meta',
    )
    field_string = fields.Char(
        string='Field Label', store=True,
        compute='_compute_field_meta',
    )
    field_type = fields.Char(
        string='Field Type', store=True,
        compute='_compute_field_meta',
    )

    @api.depends('field_id', 'field_id.name', 'field_id.field_description', 'field_id.ttype')
    def _compute_field_meta(self):
        for rec in self:
            if rec.field_id:
                rec.field_name   = rec.field_id.name
                rec.field_string = rec.field_id.field_description
                rec.field_type   = rec.field_id.ttype  # Selection value stored as Char
            else:
                rec.field_name   = False
                rec.field_string = False
                rec.field_type   = False
    is_custom = fields.Boolean(
        string='Custom Field',
        help='True if this field was created by the Dynamic API Builder module.',
        default=False,
    )
    alias = fields.Char(
        string='JSON Key Alias',
        help='Optional: override the JSON key name in the API response/request. '
             'Leave empty to use the Odoo field name.',
    )
    is_readonly = fields.Boolean(
        string='Read-Only',
        help='If checked, this field is excluded from POST/PUT request bodies.',
        default=False,
    )
    sequence = fields.Integer(string='Sequence', default=10)

    # ─────────────────────────────────────────────────────────────────────────
    # Constraints
    # ─────────────────────────────────────────────────────────────────────────

    @api.constrains('field_id', 'endpoint_id')
    def _check_field_belongs_to_model(self):
        for rec in self:
            if rec.field_id and rec.endpoint_id.model_id:
                if rec.field_id.model_id != rec.endpoint_id.model_id:
                    raise ValidationError(_(
                        'Field "%(field)s" does not belong to model "%(model)s".',
                        field=rec.field_id.name,
                        model=rec.endpoint_id.model_name,
                    ))

    @api.constrains('alias')
    def _check_alias_format(self):
        for rec in self:
            if rec.alias:
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', rec.alias.strip()):
                    raise ValidationError(_(
                        'Alias "%s" is invalid. Use only letters, digits, and underscores, '
                        'starting with a letter or underscore.', rec.alias,
                    ))

    # ─────────────────────────────────────────────────────────────────────────
    # Dynamic field creation
    # ─────────────────────────────────────────────────────────────────────────

    @api.model
    def create_field_on_model(self, endpoint_id, field_vals):
        """
        Dynamically add a new column to an Odoo model using ir.model.fields.

        This is the bridge between the UI "Add Custom Field" dialog and Odoo's
        meta-model layer.  The field is created via ``ir.model.fields.sudo()``
        which triggers Odoo's ORM schema migration (ALTER TABLE) immediately.

        Parameters
        ----------
        endpoint_id : int
            ID of the dynamic.api.endpoint that owns this field.
        field_vals : dict
            Expected keys:
              - field_label (str)       – user-visible label
              - field_name  (str)       – technical name (must start with x_)
              - field_type  (str)       – Odoo ttype, e.g. 'char', 'integer'
              - required    (bool)
              - default_value (str|None)

        Returns
        -------
        dict  with keys  id, name, field_description, ttype  of the new field.
        """
        endpoint = self.env['dynamic.api.endpoint'].sudo().browse(endpoint_id)
        if not endpoint.exists():
            raise UserError(_('Endpoint not found: %s') % endpoint_id)
        if not endpoint.allow_create_field:
            raise UserError(_(
                'This endpoint is not configured to allow custom field creation.'
            ))

        model_id = endpoint.model_id
        field_name = field_vals.get('field_name', '').strip()

        # Odoo requires custom fields to start with x_
        if not field_name.startswith('x_'):
            field_name = 'x_' + field_name
        if not re.match(r'^x_[a-z_][a-z0-9_]*$', field_name):
            raise UserError(_(
                'Invalid technical name "%s". Must be lowercase letters, digits, '
                'and underscores only (will be prefixed with x_).', field_name,
            ))

        # Check for collision
        existing = self.env['ir.model.fields'].sudo().search([
            ('model_id', '=', model_id.id),
            ('name', '=', field_name),
        ], limit=1)
        if existing:
            raise UserError(_(
                'Field "%s" already exists on model "%s".',
                field_name, model_id.model,
            ))

        ttype = field_vals.get('field_type', 'char')
        ALLOWED_TYPES = {
            'char', 'text', 'integer', 'float', 'boolean',
            'date', 'datetime', 'selection', 'many2one',
        }
        if ttype not in ALLOWED_TYPES:
            raise UserError(_('Field type "%s" is not supported for dynamic creation.') % ttype)

        new_field_vals = {
            'name': field_name,
            'field_description': field_vals.get('field_label', field_name),
            'model_id': model_id.id,
            'ttype': ttype,
            'required': bool(field_vals.get('required', False)),
            'store': True,
            'copied': True,
            'state': 'manual',  # marks as user-defined
        }
        if ttype == 'char' and field_vals.get('default_value'):
            new_field_vals['default'] = field_vals['default_value']

        # This triggers Odoo's ORM to ALTER TABLE immediately
        ir_field = self.env['ir.model.fields'].sudo().create(new_field_vals)

        # Create the dynamic.api.field linking record
        api_field = self.sudo().create({
            'endpoint_id': endpoint_id,
            'field_id': ir_field.id,
            'is_custom': True,
            'sequence': 100,
        })

        _logger.info(
            'DynamicAPI: created custom field %s on model %s (endpoint=%s, api_field=%s)',
            field_name, model_id.model, endpoint_id, api_field.id,
        )

        return {
            'id': ir_field.id,
            'name': ir_field.name,
            'field_description': ir_field.field_description,
            'ttype': ir_field.ttype,
            'api_field_id': api_field.id,
        }

    def unlink(self):
        """
        If we own the ir.model.fields record (is_custom=True), drop it too.
        This cascades the schema change automatically via Odoo ORM.
        """
        custom_field_ids = self.filtered('is_custom').mapped('field_id.id')
        result = super().unlink()
        if custom_field_ids:
            custom_fields = self.env['ir.model.fields'].sudo().browse(custom_field_ids).exists()
            # Only delete if no other endpoint still references them
            for f in custom_fields:
                still_used = self.search([('field_id', '=', f.id)], limit=1)
                if not still_used:
                    try:
                        f.unlink()
                    except Exception as e:
                        _logger.warning(
                            'DynamicAPI: could not delete custom field %s: %s', f.name, e
                        )
        return result
