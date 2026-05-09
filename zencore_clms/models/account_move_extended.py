from odoo import models
from odoo.exceptions import UserError, AccessError


class AccountMoveExtended(models.Model):
    """
    Invoice Hook — account.move extension.

    Hooks implemented:
    ──────────────────
    1. action_post()       → Invoice posted → Bucket 1 → Bucket 2 (SRS §3.3)
    2. _clm_check_payment_state() → Called from AccountPaymentExtended after
                                    payment is posted and reconciled.

    SoD (SRS §10):
    ──────────────
    - action_post(): TDO posts invoices (NOT Finance — Finance handles payment).
    - Payment registration: Finance only (enforced in AccountPaymentExtended).

    SRS §6.2 compliance:
    ─────────────────────
    - Invoice posting: ALLOWED even when frozen.
    - Payment registration: ALLOWED even when frozen.
    - NO freeze check in this file.
    """

    _inherit = 'account.move'

    def action_post(self):
        """
        SRS §3.3: Invoice posted → move related sale orders Bucket 1 → Bucket 2.
        SoD: TDO posts invoices. Finance does NOT post invoices.
        Allowed even when group is frozen (SRS §6.2).

        FIX from v0.2.0: Was checking group_zencore_clm_finance — WRONG.
        Per SRS §10, TDO creates and posts invoices. Finance handles payment only.
        """
        # if not self.env.user.has_group('zencore_clms.group_zencore_clm_tdo'):
        #     raise AccessError(
        #         "Only TDO (Territory/Technical Delivery Officer) can post invoices.\n"
        #         "SoD rule: Invoice posting is separate from payment handling."
        #     )

        result = super().action_post()

        # After posting, move all linked sale orders from Bucket 1 → Bucket 2
        for move in self.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
        ):
            sale_orders = (
                move.invoice_line_ids
                .mapped('sale_line_ids')
                .mapped('order_id')
            )
            if sale_orders:
                sale_orders._clm_move_to_bucket2()

        return result


class AccountPaymentExtended(models.Model):
    """
    Payment Hook — account.payment extension.

    SRS §3.6: Full payment received → Bucket 4 → Paid.
    SRS §4.3: Payment allowed only after bank acceptance.
    SRS §6.2: Payment ALLOWED even when frozen.
    SoD: Finance handles payment registration.

    FIX from v0.2.0:
    ─────────────────
    Original code overrode account.move.line.reconcile() but:
      1. Never called super().reconcile() — reconciliation never happened.
      2. Used incorrect `self - line` logic to find invoice lines.
      3. _post_reconcile_hook() does not exist in Odoo 19.

    Correct approach: Override account.payment.action_post().
    After payment is posted, Odoo auto-reconciles with the invoice.
    reconciled_invoice_ids is available immediately after action_post().
    We check bank_acceptance BEFORE allowing payment and detect paid state AFTER.
    """

    _inherit = 'account.payment'

    def action_post(self):
        """
        SoD: Finance posts payments.
        Pre-check: Bank acceptance must be confirmed before payment (SRS §4.3).
        Post-action: Detect fully paid invoices and move to 'paid' CLM stage.
        Allowed even when frozen (SRS §6.2).
        """
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
            raise AccessError(
                "Only Finance can register and post payments."
            )

        # Pre-check: Bank acceptance required for all related sale orders
        for payment in self.filtered(lambda p: p.partner_type == 'customer'):
            self._clm_assert_bank_acceptance(payment)

        result = super().action_post()

        # Post-action: after Odoo reconciles payment with invoice,
        # check if any invoice is now fully paid → move to CLM 'paid' stage.
        # for payment in self.filtered(lambda p: p.partner_type == 'customer'):
        #     self._clm_propagate_paid_state(payment)

        for payment in self.filtered(lambda p: p.partner_type == 'customer'):
            invoices = payment.reconciled_invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice'
            )

            # Force recompute/refetch
            invoices.invalidate_recordset()

            paid_invoices = invoices.filtered(
                lambda inv: inv.payment_state == 'paid'
            )

            if paid_invoices:
                sale_orders = (
                    paid_invoices.invoice_line_ids
                    .mapped('sale_line_ids')
                    .mapped('order_id')
                )

                sale_orders._clm_move_to_paid()

                return result

    def _clm_assert_bank_acceptance(self, payment):
        """
        Validates that all sale orders linked to this payment's reconciled
        invoices have bank acceptance confirmed. Raises UserError if not.
        SRS §4.3: Payment registration available only after bank acceptance.
        """
        # Find invoices that will be reconciled by this payment
        # At pre-post stage, we look at payment lines' matched moves
        linked_invoices = payment.invoice_ids  # invoices directly linked at payment wizard
        if not linked_invoices:
            return

        for invoice in linked_invoices.filtered(
            lambda m: m.move_type == 'out_invoice'
        ):
            sale_orders = (
                invoice.invoice_line_ids
                .mapped('sale_line_ids')
                .mapped('order_id')
                .filtered(lambda o: o.state != 'cancel' and o.clm_state != 'paid')
            )
            not_bank_accepted = sale_orders.filtered(lambda o: not o.clm_bank_acceptance)
            if not_bank_accepted:
                refs = ', '.join(not_bank_accepted.mapped('name'))
                raise UserError(
                    f"⛔  Payment Blocked — Bank Acceptance Required\n\n"
                    f"The following orders have not received bank acceptance:\n"
                    f"{refs}\n\n"
                    f"Record bank acceptance before registering payment."
                )

    def _clm_propagate_paid_state(self, payment):
        """
        After payment is posted and reconciled, find invoices that are now
        fully paid and move their sale orders from Bucket 4 → Paid.
        SRS §3.6.
        """
        # reconciled_invoice_ids is a computed field available after action_post()
        for invoice in payment.reconciled_invoice_ids.filtered(
            lambda m: (
                m.move_type == 'out_invoice'
                and m.payment_state in ('paid', 'in_payment')
            )
        ):
            sale_orders = (
                invoice.invoice_line_ids
                .mapped('sale_line_ids')
                .mapped('order_id')
            )
            if sale_orders:
                sale_orders._clm_move_to_paid()
