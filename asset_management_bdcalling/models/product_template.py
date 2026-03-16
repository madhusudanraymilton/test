# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_asset = fields.Boolean(
        string='Is an Asset',
        default=False,
        help='Enable if this product is registered as an asset in the Asset Management System.',
    )
    
    asset_category_id = fields.Many2one(
        'account.asset',
        string='Asset Category',
        domain=[('state', '=', 'model')],
    )

    tracking = fields.Selection(
        selection_add=[],
    )

    @api.onchange('is_asset')
    def _onchange_is_asset(self):
        """
        If product is marked as asset,
        force tracking to serial number.
        """
        if self.is_asset:
            self.tracking = 'serial'

    @api.constrains('is_asset', 'tracking')
    def _check_asset_tracking(self):
        """
        Prevent saving asset product without serial tracking.
        """
        for record in self:
            if record.is_asset and record.tracking != 'serial':
                raise ValidationError(
                    "Asset products must use Serial Number tracking."
                )