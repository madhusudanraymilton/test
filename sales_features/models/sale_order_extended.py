# from odoo import models, fields, api

# class SalesOrderExtended(models.Model):
#     _inherit = 'sale.order'

#     profile_id = fields.Many2one('bd.profile.name', string="Profile")

#     @api.onchange('profile_id')
#     def _onchange_profile_id(self):
#         self.env['account.move'].sudo().create({
#             'profile_id':self.profile_id.id
#         })


from odoo.exceptions import UserError
from itertools import groupby
from odoo import models, fields, _ , api
from odoo.exceptions import UserError


from odoo import Command  # used in _create_invoices for invoice line creation

# ============================================================
# Extend account.move to add profile_id field
# ============================================================
# class AccountMoveExtended(models.Model):
#     _inherit = 'account.move'

#     # Many2one field to store the profile from sale.order
#     profile_id = fields.Many2one('bd.profile.name', string="Profile")


# ============================================================
# Extend sale.order to add profile_id field and propagate it to invoices
# ============================================================
class SaleOrderExtended(models.Model):
    _inherit = 'sale.order'

    # Many2one field to store profile
    profile_id = fields.Many2one('bd.profile.name', string="Profile")

    # ============================================================
    # Override _create_invoices to propagate profile_id safely
    # ============================================================
    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        Create invoice(s) for the given Sales Order(s) and propagate profile_id
        :param bool grouped: if True, invoices are grouped by SO id
        :param bool final: if True, refunds will be generated if necessary
        :param date: unused parameter
        :returns: account.move recordset
        """
        # ============================================================
        # 0) Access check
        # ============================================================
        if not self.env['account.move'].has_access('create'):
            try:
                self.check_access('write')
            except UserError:
                return self.env['account.move']

        # ============================================================
        # 1) Prepare invoices
        # ============================================================
        invoice_vals_list = []
        invoice_item_sequence = 0  # To keep invoice line order

        for order in self:
            # Ensure correct language and company context
            if order.partner_invoice_id.lang:
                order = order.with_context(lang=order.partner_invoice_id.lang)
            order = order.with_company(order.company_id)

            # Prepare invoice values
            invoice_vals = order._prepare_invoice()

            # ====== NEW: Add profile_id to invoice_vals ======
            invoice_vals['profile_id'] = order.profile_id.id if order.profile_id else False

            # Prepare invoice lines
            invoiceable_lines = order._get_invoiceable_lines(final)
            if all(line.display_type for line in invoiceable_lines):
                continue  # Skip if all lines are section/notes

            invoice_line_vals = []
            down_payment_section_added = False

            for line in invoiceable_lines:
                # Down payment section handling
                if not down_payment_section_added and line.is_downpayment:
                    invoice_line_vals.append(
                        Command.create(
                            order._prepare_down_payment_section_line(sequence=invoice_item_sequence)
                        )
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1

                optional_values = {'sequence': invoice_item_sequence}

                # Adjust for final invoice downpayments
                if line.is_downpayment:
                    optional_values['quantity'] = -1.0
                    optional_values['extra_tax_data'] = self.env['account.tax']\
                        ._reverse_quantity_base_line_extra_tax_data(line.extra_tax_data)

                # Add prepared invoice line vals
                for vals in line._prepare_invoice_lines_vals_list(**optional_values):
                    invoice_line_vals.append(Command.create(vals))
                    # invoice_line_vals.append((0, 0, vals))

                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list and self.env.context.get('raise_if_nothing_to_invoice', True):
            raise UserError(self._nothing_to_invoice_error_message())

        # ============================================================
        # 2) Handle 'grouped' invoices
        # ============================================================
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(
                invoice_vals_list,
                key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]
            )

            for _grouping_keys, invoices in groupby(invoice_vals_list,
                                                    key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # ============================================================
        # 3) Create invoices
        # ============================================================
        moves = self._create_account_invoices(invoice_vals_list, final)

        # ====== Ensure profile_id is set on moves (safe approach) ======
        for order, move in zip(self, moves):
            move.profile_id = order.profile_id
            move._onchange_profile_id()
        # ============================================================
        # 4) Handle refunds for final invoices
        # ============================================================
        if final and (moves_to_switch := moves.sudo().filtered(lambda m: m.amount_total < 0)):
            with self.env.protecting([moves._fields['team_id']], moves_to_switch):
                moves_to_switch.action_switch_move_type()
                self.invoice_ids._set_reversed_entry(moves_to_switch)

        # ============================================================
        # 5) Post messages linking invoice to sale order
        # ============================================================
        for move in moves:
            move.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': move, 'origin': move.line_ids.sale_line_ids.order_id},
                subtype_xmlid='mail.mt_note',
            )

        # ============================================================
        # 6) Return created invoices
        # ============================================================
        return moves

# ============================================================
# END OF FILE
# ============================================================




#   Overall work is that --- One click ei all done/paid
 
 
    def action_confirm(self):
        res = super().action_confirm()

        for order in self:

            # 1. Set delivered quantity
            for line in order.order_line:
                if line.product_id.type in ('product', 'consu'):
                    line.qty_delivered = line.product_uom_qty

            # 2. Create invoice if not exists
            invoices = order.invoice_ids.filtered(lambda i: i.state != 'cancel')
            if not invoices:
                invoices = order._create_invoices()

            for invoice in invoices:

                # 3. Post invoice
                if invoice.state == 'draft':
                    invoice.action_post()

                # 4. Validate profile and journal
                if not order.profile_id:
                    raise UserError(_("Please set a Profile on the Sale Order."))

                if not order.profile_id.journal_id:
                    raise UserError(_("Please set a Journal on the selected Profile."))

                journal = order.profile_id.journal_id

                # # 5. Register payment
                # payment_wizard = self.env['account.payment.register'].with_context(
                #     active_model='account.move',
                #     active_ids=invoice.ids,
                # ).create({
                #     'journal_id': journal.id,
                #     'amount': invoice.amount_residual,
                #     'payment_date': fields.Date.context_today(self),
                # })

                # # 6. Pay invoice → PAID
                # payment_wizard.action_create_payments()

        return res