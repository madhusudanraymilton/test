# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_asset = fields.Boolean(
        string='Is an Asset',
        default=False,
        help='Enable if this product is registered as an asset in the Asset Management System.',
    )
    asset_category_id = fields.Many2one(
        'asset.category',
        string='Default Asset Category',
        domain="[('company_id', '=', company_id)]",
        help='Default category to pre-fill when registering this product as an asset.',
    )

    @api.onchange('is_asset')
    def _onchange_is_asset(self):
        if not self.is_asset:
            self.asset_category_id = False
