# -*- coding: utf-8 -*-
from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_ids = fields.One2many(
        'account.asset',
        'vendor_bill_line_id',
        string='Assets'
    )