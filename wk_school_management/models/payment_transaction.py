# -*- coding: utf-8 -*-
#################################################################################
#
# Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>; )
# See LICENSE file for full copyright and licensing details.
# License URL : <https://store.webkul.com/license.html/>;
#
#################################################################################

from odoo import models, fields, api, _, Command, SUPERUSER_ID
import logging
import base64

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    fee_slip_ids = fields.Many2many('wk.fee.slip', string='Fee Slips', copy=False, readonly=True)
    fee_slip_ids_nbr = fields.Integer(compute='_compute_fee_slip_ids_nbr', string='# of Fee Slips')

    @api.depends('fee_slip_ids')
    def _compute_fee_slip_ids_nbr(self):
        for trans in self:
            trans.fee_slip_ids_nbr = len(trans.fee_slip_ids)

    def _log_message_on_linked_documents(self, message):
        author = self.env.user.partner_id if self.env.uid == SUPERUSER_ID else self.partner_id
        if self.source_transaction_id:
            for invoice in self.source_transaction_id.invoice_ids:
                invoice.message_post(body=message, author_id=author.id)
            payment_id = self.source_transaction_id.payment_id
            if payment_id:
                payment_id.message_post(body=message, author_id=author.id)
        for slip in self.fee_slip_ids or self.source_transaction_id.fee_slip_ids:
            slip.message_post(body=message, author_id=author.id)

    def _check_fee_and_confirm(self):
        confirmed_orders = self.env['wk.fee.slip']
        for tx in self:
            if len(tx.fee_slip_ids) == 1:
                slip = tx.fee_slip_ids.filtered(lambda fs: fs.state in ('to_pay', 'overdue'))
                if slip:
                    slip.state = 'paid'
                    confirmed_orders |= slip
        return confirmed_orders

    def _invoice_fee_slips(self):
        for tx in self.filtered(lambda tx: tx.fee_slip_ids):
            tx = tx.with_company(tx.company_id)

            confirmed_slips = tx.fee_slip_ids.filtered(lambda fs: fs.state == 'paid')
            if confirmed_slips:
                final_invoices = confirmed_slips.with_context(
                    raise_if_nothing_to_invoice=False
                )._create_invoices(final=True)
                invoices =  final_invoices
                for invoice in invoices:
                    invoice._portal_ensure_token()
                tx.invoice_ids = [Command.set(invoices.ids)]
                return invoices

    def _post_process(self):
        """Override of fee slip to automatically confirm the fee, generate invoices, and send related notifications."""
        confirmed_fee_slips = self._check_fee_and_confirm()
        if confirmed_fee_slips and not confirmed_fee_slips.invoice_id:
            self._invoice_fee_slips()
        else:
            confirmed_fee_slips.invoice_id.action_post()
            if not self.fee_slip_ids:
                self.fee_slip_ids = confirmed_fee_slips = self.invoice_ids.fee_slip_id
                self.fee_slip_ids.state = 'paid'
            confirmed_fee_slips.invoice_id.payment_state = 'paid'
        super()._post_process()

        if confirmed_fee_slips.invoice_id and confirmed_fee_slips.invoice_id.state == 'posted':
            mail_template = self.env.ref('wk_school_management.fee_slip_success_mail', raise_if_not_found=False)
            if mail_template:
                report_action = self.env['ir.actions.report']\
                    .with_context(force_report_rendering=True)\
                    ._render('account.account_invoices', confirmed_fee_slips.invoice_id.id)

                report_base64 = base64.b64encode(report_action[0])
                attachment = self.env['ir.attachment'].create({
                'name': f'Invoice_{confirmed_fee_slips.invoice_id.name}.pdf',
                'type': 'binary',
                'datas': report_base64,
                'res_model': 'wk.fee.slip',
                'res_id': confirmed_fee_slips.id,
                'mimetype': 'application/pdf',
                })

                mail_template.attachment_ids = attachment
                mail_template.send_mail(confirmed_fee_slips.id)

    def action_view_fee_slip(self):
        action = {
            'name': _('Fee Slip(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'wk.fee.slip',
            'target': 'current',
        }
        fee_slip_ids = self.fee_slip_ids.ids
        if len(fee_slip_ids) == 1:
            action['res_id'] = fee_slip_ids[0]
            action['view_mode'] = 'form'
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', fee_slip_ids)]
        return action