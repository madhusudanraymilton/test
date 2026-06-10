from odoo import models
from odoo.exceptions import AccessError


class AccountPaymentRegisterExtended(models.TransientModel):
    """
    Register Payment Wizard Hook — account.payment.register extension.

    WHY action_create_payments() and NOT account.payment.action_post():
    ────────────────────────────────────────────────────────────────────
    In Odoo 17+, account.payment.register._create_payments() runs in two steps:

        Step 1: _post_payments(payments)       → fires account.payment.action_post()
        Step 2: _reconcile_payments(to_process) → reconciles entries with invoices

    AccountPaymentExtended.action_post() fires at Step 1 — BEFORE reconciliation.
    payment.reconciled_invoice_ids is EMPTY at that point (Step 2 hasn't run),
    so _clm_update_payment_stage() is never triggered.

    This override fires AFTER _create_payments() returns — meaning both steps are
    complete, invoice.payment_state is accurate, and stage advancement is safe.

    AccountPaymentExtended.action_post() is retained for programmatic payment flows
    (bank statement auto-reconcile, SEPA batches) that bypass this wizard entirely.
    """

    _inherit = 'account.payment.register'

    def action_create_payments(self):
        """
        Trigger CLM stage update AFTER posting + reconciliation complete.

        self.line_ids = receivable/payable journal items of the invoices being paid.
        These are populated from active_ids when the wizard opens.
        After super(), their move_id.payment_state reflects real post-payment values.
        """
        # SoD gate: only Finance may register payments (SRS §10)
        # Checked here so the wizard is blocked before any write happens.
        if not self.env.user.has_group('zencore_groups.group_zencore_clm_finance'):
            raise AccessError(
                "Only Finance can register payments for customer invoices.\n"
                "SRS §10 — Separation of Duties."
            )

        # super() runs _post_payments() + _reconcile_payments() atomically.
        # By the time it returns, payment_state on all affected invoices is current.
        result = super().action_create_payments()

        # Get the invoices that were just paid.
        # self.line_ids are the receivable lines; move_id gives the invoice.
        invoices = self.line_ids.move_id.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
        )
        if not invoices:
            return result

        # Flush ORM cache — force re-read from DB after reconciliation writes
        invoices.invalidate_recordset(['payment_state', 'amount_residual'])

        # Find linked sale orders and advance their CLM operational stage
        sale_orders = (
            invoices.invoice_line_ids
            .mapped('sale_line_ids')
            .mapped('order_id')
            .filtered(lambda o: o.state not in ('cancel', 'draft'))
        )
        if sale_orders:
            sale_orders._clm_update_payment_stage()

        return result