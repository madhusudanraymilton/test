# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    asset_location_id = fields.Many2one(
        'stock.location',
        string='Default Asset Location',
        related='company_id.asset_location_id',
        readonly=False,
        domain="[('usage', '=', 'inventory')]",
        help='Default stock location where registered assets are moved to.',
    )

    auto_return_on_employee_archive = fields.Boolean(
        string='Auto-Return Assets on Employee Archive',
        related='company_id.auto_return_on_employee_archive',
        readonly=False,
        help='Automatically return all assets when an employee is archived.',
    )

    asset_assign_date_future_allowed = fields.Boolean(
        string='Allow Future Assignment Dates',
        related='company_id.asset_assign_date_future_allowed',
        readonly=False,
        help='Allow setting an assignment date in the future.',
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    asset_location_id = fields.Many2one(
        'stock.location',
        string='Default Asset Location',
        domain="[('usage', '=', 'inventory')]",
    )
    auto_return_on_employee_archive = fields.Boolean(
        string='Auto-Return Assets on Employee Archive',
        default=False,
    )
    asset_assign_date_future_allowed = fields.Boolean(
        string='Allow Future Assignment Dates',
        default=False,
    )
