# -*- coding: utf-8 -*-
from odoo import api, fields, models, _ 
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_asset = fields.Boolean(
        string='Is an Asset',
        default=False,
        help='Enable if this product is registered as an asset in the Asset Management System.',
    )
    # Points to Odoo's native account.asset "model" records (asset templates),
    # kept separate from asset.category which is the AMS-internal category.
    asset_category_id = fields.Many2one(
        'account.asset',
        string='Default Asset Category',
        domain="[('state', '=', 'model')]",
        help='Odoo native asset category used for accounting integration.',
    )

    # FIX: removed the useless `tracking = fields.Selection(selection_add=[])`
    # override that did nothing but potentially caused ORM confusion.

    @api.onchange('is_asset')
    def _onchange_is_asset(self):
        """Force serial-number tracking when product is flagged as an asset."""
        if self.is_asset:
            self.tracking = 'serial'

    @api.constrains('is_asset', 'tracking')
    def _check_asset_tracking(self):
        """Prevent saving an asset product without serial tracking."""
        for record in self:
            if record.is_asset and record.tracking != 'serial':
                raise ValidationError(
                    _('Asset products must use Serial Number tracking.')
                )
