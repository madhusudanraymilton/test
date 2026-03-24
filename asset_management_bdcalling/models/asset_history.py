# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssetHistory(models.Model):
    _name = 'asset.history'
    _description = 'Asset Lifecycle History'
    _order = 'event_date desc'
    _rec_name = 'event_type'

    asset_id = fields.Many2one(
        'account.asset',
        string='Asset',
        required=True,
        ondelete='cascade',
        index=True,
    )
    serial_number = fields.Char(
        string='Serial Number',
        related='asset_id.lot_id.name',
        readonly=True,
        compute='_compute_serial_number',
        store=True,
    )
    event_type = fields.Selection(
        selection=[
            ('register', 'Registered'),
            ('unregister', 'Unregistered'),
            ('assign', 'Assigned'),
            ('return', 'Returned'),
            ('depreciate', 'Depreciated'),
            ('scrap', 'Scrapped'),
            ('dispose', 'Disposed'),
            ('note', 'Note'),
        ],
        string='Event Type',
        required=True,
        index=True,
    )
    event_date = fields.Datetime(
        string='Event Date',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    old_state = fields.Char(string='Previous State', readonly=True)
    new_state = fields.Char(string='New State', readonly=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        ondelete='set null',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Performed By',
        required=True,
        default=lambda self: self.env.uid,
        readonly=True,
    )
    description = fields.Text(string='Description')
    metadata = fields.Json(string='Metadata')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    @api.depends('asset_id.lot_id')
    def _compute_serial_number(self):
        for record in self:
            record.serial_number = record.asset_id.lot_id.name if record.asset_id.lot_id else False

    # ─── Append-only enforcement ────────────────────────────────────────────

    def write(self, vals):
        raise UserError(_(
            'Asset history records are immutable and cannot be modified. '
            'This is an audit log.'
        ))

    def unlink(self):
        raise UserError(_(
            'Asset history records cannot be deleted. '
            'This is a permanent audit log.'
        ))
