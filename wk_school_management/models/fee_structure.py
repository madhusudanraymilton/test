# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################

from odoo import models, fields
import logging
import base64
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    is_fee_element = fields.Boolean(string='Is Fee Element?', default=False)


class FeeComponent(models.Model):

    _name = "fee.component"
    _description = "Fee Component"
    _order = "sequence desc"

    sequence = fields.Integer(required=True, default=10)
    product_id = fields.Many2one('product.product', string="Fee Element",
                                 required=True, domain="[('is_fee_element','=',True)]")
    fee = fields.Float(string="Fee", required=True)
    frequency = fields.Selection(
        [('one', 'Once'), ('multi', 'Recurring')], string="Frequency", required=True)
    structure_id = fields.Many2one('fee.structure', string="Fee Structure")


class FeeStructure(models.Model):

    _name = "fee.structure"
    _inherit = "wk.company.visibility.mixin"
    _description = "Fee Structure"

    name = fields.Char(string="Title", required=True)
    company_id = fields.Many2one(
        'res.company', string="School", required=True, default=lambda self: self.env.company)
    grade_id = fields.Many2one('wk.school.grade', string="Class",
                               required=True, domain="[('company_id','=',company_id)]")
    fee_component_ids = fields.One2many(
        "fee.component", 'structure_id', string="Fee Components")
    late_fee_enable = fields.Boolean(string='Enable late fee?')
    late_fee_amount = fields.Float(string='Late fee charges')
    description = fields.Html(string='Terms and Conditions')
    currency_id = fields.Many2one('res.currency', string="Currency", required=True)


class AccountMove(models.Model):
    _inherit = "account.move"

    fee_slip_id = fields.Many2one('wk.fee.slip', string='Fee Slip', copy=False, readonly=True)

    def get_fee_slip_id(self):
        self.ensure_one()
        fee_slip_id = self.env['wk.fee.slip'].search(
            [('invoice_id', '=', self.id)])
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'wk.fee.slip',
            'view_mode': 'form',
            'res_id': fee_slip_id.id,
            'views': [[self.env.ref('wk_school_management.wk_fee_slip_view_form').id, 'form']],
        }
        return action


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        res = super().action_create_payments()
        if self.line_ids.move_id.payment_state == 'paid':
            self.line_ids.move_id.fee_slip_id.state = 'paid'
            mail_template = self.env.ref('wk_school_management.fee_slip_success_mail', raise_if_not_found=False)
            if mail_template:
                report_action = self.env['ir.actions.report']\
                    .with_context(force_report_rendering=True)\
                    ._render('account.account_invoices', self.line_ids.move_id.id)

                report_base64 = base64.b64encode(report_action[0])
                attachment = self.env['ir.attachment'].create({
                        'name': f'Invoice_{self.line_ids.move_id.name}.pdf',
                        'type': 'binary',
                        'datas': report_base64,
                        'res_model': 'wk.fee.slip',
                        'res_id': self.line_ids.move_id.fee_slip_id.id,
                        'mimetype': 'application/pdf',
                })

                mail_template.attachment_ids = attachment
                mail_template.send_mail(self.line_ids.move_id.fee_slip_id.id)
