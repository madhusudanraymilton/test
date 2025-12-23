# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_id = fields.Many2one('product.product', string="Late Fee Element", domain="[('is_fee_element','=',True)]")
    scholarship_product_id = fields.Many2one('product.product', string="Scholarship Element", domain="[('is_fee_element','=',True)]")
    no_of_days = fields.Integer(string="Days to confirm the fee slip before")
    card_layout = fields.Selection([
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical')
    ], string="Card Layout", config_parameter='wk_school_management.card_layout')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()

        IrDefault.set('res.config.settings', 'product_id', self.product_id.id)
        IrDefault.set('res.config.settings', 'no_of_days', self.no_of_days)
        IrDefault.set('res.config.settings',
                      'scholarship_product_id', self.scholarship_product_id.id)
        IrDefault.set('res.config.settings',
                      'card_layout', self.card_layout)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefaultGet = self.env['ir.default'].sudo()._get
        product_id = IrDefaultGet('res.config.settings', 'product_id')
        scholarship_product_id = IrDefaultGet('res.config.settings', 'scholarship_product_id')
        no_of_days = IrDefaultGet('res.config.settings', 'no_of_days') or 10
        card_layout = IrDefaultGet('res.config.settings', 'card_layout') or 'horizontal'
        res.update(
            scholarship_product_id=scholarship_product_id,
            product_id=product_id,
            no_of_days=no_of_days,
            card_layout=card_layout)
        return res
