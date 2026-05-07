from odoo import models
from odoo.exceptions import UserError

class AccountMoveExtended(models.Model):
    """
    Invoice and Payment Hooks.

    Hooks:
      - action_post(): Invoice posted → Bucket 1 → Bucket 2
      - (payment) reconcile(): Full payment detected → Bucket 4 → Paid

    Note: Invoice posting is ALLOWED even when frozen (SRS §6.2).
    Payment registration is ALLOWED even when frozen (SRS §6.2).
    No freeze check is applied here.
    """

    _inherit = 'account.move'

    def action_post(self):
        """
        After posting a customer invoice, move related sale orders
        from Bucket 1 → Bucket 2.

        Uses sale_line_ids (Many2many on account.move.line → sale.order.line)
        which is set up by Odoo's sale module.
        """
        result = super().action_post()

        for move in self.filtered(lambda m: m.move_type == 'out_invoice' and m.state == 'posted'):
            sale_orders = (
                move.invoice_line_ids
                .mapped('sale_line_ids')
                .mapped('order_id')
            )
            if sale_orders:
                sale_orders._clm_move_to_bucket2()

        return result


# class AccountMoveLineExtended(models.Model):
#     """
#     Reconciliation Hook.

#     When a move line is reconciled (payment applied to invoice),
#     check if the invoice is now fully paid.
#     If yes → move sale order from Bucket 4 → Paid.

#     This is the most reliable hook for detecting full payment in Odoo,
#     since payment_state is a computed field that updates post-reconcile.
#     """

#     _inherit = 'account.move.line'

#     def reconcile(self):
#         result = super().reconcile()

#         # Collect all invoices touched by this reconciliation
#         touched_invoices = self.mapped('move_id').filtered(
#             lambda m: m.move_type == 'out_invoice'
#         )

#         for invoice in touched_invoices:
#             # payment_state is recomputed after super().reconcile()
#             if invoice.payment_state in ('paid', 'in_payment'):
#                 sale_orders = (
#                     invoice.invoice_line_ids
#                     .mapped('sale_line_ids')
#                     .mapped('order_id')
#                 )
#                 if sale_orders:
#                     sale_orders._clm_move_to_paid()

#         return result

# models/account_move_extended.py — add to existing file

class AccountMoveLineExtended(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        """
        Before reconciling a receivable payment line with an invoice,
        verify bank acceptance on the related sale order.
        SRS §4.3: Payment registration allowed only after bank acceptance.
        SRS §6.2: Payment allowed even during freeze.
        """
        # Find payment lines being reconciled against customer invoices
        for line in self:
            if line.account_id.account_type != 'asset_receivable':
                continue
            if not line.payment_id:
                continue  # Not a payment line
            # Find the invoice lines being matched
            matched_invoice_lines = self - line
            for inv_line in matched_invoice_lines:
                if inv_line.move_id.move_type != 'out_invoice':
                    continue
                invoice = inv_line.move_id
                sale_orders = (
                    invoice.invoice_line_ids
                    .mapped('sale_line_ids')
                    .mapped('order_id')
                    .filtered(lambda o: o.state != 'cancel'
                              and o.clm_state not in ('paid',))
                )
                not_accepted = sale_orders.filtered(
                    lambda o: not o.clm_bank_acceptance
                )
                if not_accepted:
                    refs = ', '.join(not_accepted.mapped('name'))
                    raise UserError(
                        f"⛔  Payment Blocked — Bank Acceptance Required\n\n"
                        f"The following orders have not received bank acceptance:\n"
                        f"{refs}\n\n"
                        f"Record bank acceptance before registering payment."
                    )
                
                sale_orders._clm_move_to_paid()

        return super().reconcile()