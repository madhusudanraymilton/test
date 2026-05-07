# from odoo import models
# from odoo.exceptions import UserError


# class AccountPaymentExtended(models.Model):
#     """
#     Payment Gate — account.payment extension.

#     SRS §4.3: Payment registration must be available ONLY after bank acceptance.
#     SRS §6.2: Payment registration is ALLOWED even during freeze.

#     So the only block here is: bank acceptance not yet done.
#     We DO NOT apply freeze check — collection must never be blocked.
#     """

#     _inherit = 'account.payment'

#     def action_post(self):
#         """
#         Override payment posting.
#         Check that all related sale orders have bank_acceptance = True.
#         """
#         for payment in self:
#             payment._clm_assert_bank_accepted()
#         return super().action_post()

#     def _clm_assert_bank_accepted(self):
#         """
#         Trace: payment → reconciled invoice → sale order lines → sale order.
#         If any linked sale order does NOT have bank acceptance, block payment.
#         """
#         self.ensure_one()

#         # Resolve linked invoices via move_id reconciliation lines
#         linked_invoices = self.reconciled_invoice_ids
#         if not linked_invoices:
#             # No linked invoices at posting time — skip check
#             # (can happen for standalone payments or advance payments)
#             return

#         for invoice in linked_invoices.filtered(lambda m: m.move_type == 'out_invoice'):
#             sale_orders = (
#                 invoice.invoice_line_ids
#                 .mapped('sale_line_ids')
#                 .mapped('order_id')
#             )
#             # Filter orders still in the pipeline (not paid, not cancelled)
#             active_orders = sale_orders.filtered(
#                 lambda o: o.clm_state not in ('paid',) and o.state != 'cancel'
#             )
#             not_accepted = active_orders.filtered(lambda o: not o.clm_bank_acceptance)
#             if not_accepted:
#                 order_refs = ', '.join(not_accepted.mapped('name'))
#                 raise UserError(
#                     f"⛔  Payment Blocked\n\n"
#                     f"Bank Acceptance has not been recorded for the following orders:\n"
#                     f"{order_refs}\n\n"
#                     f"Payment registration is only allowed after bank acceptance is confirmed.\n"
#                     f"Please record bank acceptance first."
#                 )

from odoo import models
from odoo.exceptions import UserError


class AccountPaymentExtended(models.Model):
    """
    Payment Gate — account.payment extension.

    SRS §4.3: Payment registration must be available ONLY after bank acceptance.
    SRS §6.2: Payment registration is ALLOWED even during freeze.

    So the only block here is: bank acceptance not yet done.
    We DO NOT apply freeze check — collection must never be blocked.
    """

    _inherit = 'account.payment'

    def action_post(self):
        """
        Override payment posting.
        Check that all related sale orders have bank_acceptance = True.
        """
        for payment in self:
            payment._clm_assert_bank_accepted()
        return super().action_post()

    def _clm_assert_bank_accepted(self):
        """
        Trace: payment → reconciled invoice → sale order lines → sale order.
        If any linked sale order does NOT have bank acceptance, block payment.
        """
        self.ensure_one()

        # Resolve linked invoices via move_id reconciliation lines
        linked_invoices = self.reconciled_invoice_ids
        if not linked_invoices:
            # No linked invoices at posting time — skip check
            # (can happen for standalone payments or advance payments)
            return

        for invoice in linked_invoices.filtered(lambda m: m.move_type == 'out_invoice'):
            sale_orders = (
                invoice.invoice_line_ids
                .mapped('sale_line_ids')
                .mapped('order_id')
            )
            # Filter orders still in the pipeline (not paid, not cancelled)
            active_orders = sale_orders.filtered(
                lambda o: o.clm_state not in ('paid',) and o.state != 'cancel'
            )
            not_accepted = active_orders.filtered(lambda o: not o.clm_bank_acceptance)
            if not_accepted:
                order_refs = ', '.join(not_accepted.mapped('name'))
                raise UserError(
                    f"⛔  Payment Blocked\n\n"
                    f"Bank Acceptance has not been recorded for the following orders:\n"
                    f"{order_refs}\n\n"
                    f"Payment registration is only allowed after bank acceptance is confirmed.\n"
                    f"Please record bank acceptance first."
                )