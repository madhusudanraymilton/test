# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AssetAssignment(models.Model):
    _name = 'asset.assignment'
    _description = 'Asset Assignment Record'
    _order = 'assign_date desc'

    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
        ondelete='restrict',
        index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
    )
    assign_date = fields.Date(
        string='Assignment Date',
        required=True,
        default=fields.Date.today,
    )
    return_date = fields.Date(string='Return Date')
    assigned_by = fields.Many2one(
        'res.users',
        string='Assigned By',
        required=True,
        default=lambda self: self.env.uid,
    )
    returned_by = fields.Many2one(
        'res.users',
        string='Returned By',
        ondelete='set null',
    )
    condition_on_assign = fields.Selection(
        selection=[
            ('new', 'New'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        string='Condition on Assignment',
    )
    condition_on_return = fields.Selection(
        selection=[
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
            ('damaged', 'Damaged'),
        ],
        string='Condition on Return',
    )
    notes = fields.Text(string='Notes')
    is_active = fields.Boolean(
        string='Currently Active',
        default=True,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    line_ids = fields.One2many(
        'asset.assignment.line',
        'assignment_id',
        string='Assignment Lines'
    )

    def init(self):
        """
        Partial unique index: only one active (non-returned) assignment per asset.
        Cannot be expressed via _sql_constraints (no partial index support in ORM).
        """
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS asset_assignment_active_unique
            ON asset_assignment (asset_id)
            WHERE (is_active = true AND return_date IS NULL)
        """)

    @api.constrains('asset_id', 'is_active', 'return_date')
    def _check_no_double_assignment(self):
        for rec in self:
            if rec.is_active and not rec.return_date:
                duplicate = self.search([
                    ('asset_id', '=', rec.asset_id.id),
                    ('is_active', '=', True),
                    ('return_date', '=', False),
                    ('id', '!=', rec.id),
                ])
                if duplicate:
                    raise UserError(_(
                        'Asset "%s" already has an active assignment. '
                        'Return it first before creating a new one.'
                    ) % rec.asset_id.name)

    @api.constrains('assign_date', 'return_date')
    def _check_dates(self):
        for rec in self:
            if rec.return_date and rec.assign_date and rec.return_date < rec.assign_date:
                raise ValidationError(_(
                    'Return date cannot be earlier than assignment date.'
                ))

    @api.constrains('assign_date', 'asset_id')
    def _check_assign_date_vs_registration(self):
        for rec in self:
            if rec.asset_id.registration_date and rec.assign_date:
                if rec.assign_date < rec.asset_id.registration_date:
                    raise ValidationError(_(
                        'Assignment date cannot precede the asset registration date (%s).'
                    ) % rec.asset_id.registration_date)


class AssetAssignmentLine(models.Model):
    _name = 'asset.assignment.line'
    _description = 'Asset Assignment Line'
    _order = 'event_date desc'

    assignment_id = fields.Many2one(
        'asset.assignment',
        string='Asset Assignment',
        required=True,
        ondelete='cascade',
        index=True,
    )
    event_type = fields.Selection(
        selection=[
            ('assign', 'Assigned'),
            ('return', 'Returned'),
            ('note', 'Note'),
        ],
        string='Event Type',
        required=True,
    )
    event_date = fields.Datetime(
        string='Event Date',
        required=True,
        default=fields.Datetime.now,
    )
    description = fields.Text(string='Description')