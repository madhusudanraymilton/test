# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AssetCategory(models.Model):
    _name = 'asset.category'
    _description = 'Asset Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Category Name',
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    depreciation_method = fields.Selection(
        selection=[
            ('straight_line', 'Straight Line'),
            ('declining', 'Declining Balance'),
        ],
        string='Depreciation Method',
        required=True,
        default='straight_line',
        tracking=True,
    )
    duration_months = fields.Integer(
        string='Duration (Months)',
        required=True,
        default=36,
        tracking=True,
    )
    computation_method = fields.Selection(
        selection=[
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        string='Computation Method',
        required=True,
        default='monthly',
    )
    non_depreciable_pct = fields.Float(
        string='Non-Depreciable (%)',
        default=0.0,
        digits=(5, 2),
    )
    account_asset_id = fields.Many2one(
        'account.account',
        string='Asset Account',
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    account_depreciation_id = fields.Many2one(
        'account.account',
        string='Accumulated Depreciation Account',
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    account_expense_id = fields.Many2one(
        'account.account',
        string='Depreciation Expense Account',
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Asset Journal',
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )
    asset_count = fields.Integer(
        string='Asset Count',
        compute='_compute_asset_count',
    )

    _sql_constraints = [
        (
            'name_company_unique',
            'UNIQUE(name, company_id)',
            'Category name must be unique per company.',
        ),
    ]

    @api.depends('name')
    def _compute_asset_count(self):
        for rec in self:
            rec.asset_count = self.env['asset.asset'].search_count([
                ('category_id', '=', rec.id),
                ('active', '=', True),
            ])

    @api.constrains('duration_months')
    def _check_duration_months(self):
        for rec in self:
            if rec.duration_months <= 0:
                raise ValidationError(_('Duration (Months) must be greater than 0.'))

    @api.constrains('non_depreciable_pct')
    def _check_non_depreciable_pct(self):
        for rec in self:
            if not (0.0 <= rec.non_depreciable_pct <= 100.0):
                raise ValidationError(_(
                    'Non-Depreciable percentage must be between 0 and 100.'
                ))

    @api.constrains('journal_id')
    def _check_journal_type(self):
        for rec in self:
            if rec.journal_id and rec.journal_id.type != 'general':
                raise ValidationError(_(
                    'The Asset Journal must be of type "Miscellaneous" (general).'
                ))

    def unlink(self):
        for rec in self:
            if self.env['asset.asset'].search_count([
                ('category_id', '=', rec.id),
                ('active', '=', True),
            ]):
                raise UserError(_(
                    'Cannot delete category "%s" because it has active assets linked to it.'
                ) % rec.name)
        return super().unlink()

    def action_view_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assets'),
            'res_model': 'asset.asset',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
