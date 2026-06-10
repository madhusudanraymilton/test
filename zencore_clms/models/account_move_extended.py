# # # # # from odoo import models
# # # # # from odoo.exceptions import UserError, AccessError


# # # # # class AccountMoveExtended(models.Model):
# # # # #     """
# # # # #     Invoice Hook — account.move extension.

# # # # #     Hooks implemented:
# # # # #     ──────────────────
# # # # #     1. action_post()       → Invoice posted → Bucket 1 → Bucket 2 (SRS §3.3)
# # # # #     2. _clm_check_payment_state() → Called from AccountPaymentExtended after
# # # # #                                     payment is posted and reconciled.

# # # # #     SoD (SRS §10):
# # # # #     ──────────────
# # # # #     - action_post(): TDO posts invoices (NOT Finance — Finance handles payment).
# # # # #     - Payment registration: Finance only (enforced in AccountPaymentExtended).

# # # # #     SRS §6.2 compliance:
# # # # #     ─────────────────────
# # # # #     - Invoice posting: ALLOWED even when frozen.
# # # # #     - Payment registration: ALLOWED even when frozen.
# # # # #     - NO freeze check in this file.
# # # # #     """

# # # # #     _inherit = 'account.move'

# # # # #     def action_post(self):
# # # # #         """
# # # # #         SRS §3.3: Invoice posted → move related sale orders Bucket 1 → Bucket 2.
# # # # #         SoD: TDO posts invoices. Finance does NOT post invoices.
# # # # #         Allowed even when group is frozen (SRS §6.2).

# # # # #         FIX from v0.2.0: Was checking group_zencore_clm_finance — WRONG.
# # # # #         Per SRS §10, TDO creates and posts invoices. Finance handles payment only.
# # # # #         """
# # # # #         # if not self.env.user.has_group('zencore_clms.group_zencore_clm_tdo'):
# # # # #         #     raise AccessError(
# # # # #         #         "Only TDO (Territory/Technical Delivery Officer) can post invoices.\n"
# # # # #         #         "SoD rule: Invoice posting is separate from payment handling."
# # # # #         #     )

# # # # #         result = super().action_post()

# # # # #         # After posting, move all linked sale orders from Bucket 1 → Bucket 2
# # # # #         for move in self.filtered(
# # # # #             lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
# # # # #         ):
# # # # #             sale_orders = (
# # # # #                 move.invoice_line_ids
# # # # #                 .mapped('sale_line_ids')
# # # # #                 .mapped('order_id')
# # # # #             )
# # # # #             if sale_orders:
# # # # #                 sale_orders._clm_move_to_bucket2()

# # # # #         return result


# # # # # class AccountPaymentExtended(models.Model):
# # # # #     """
# # # # #     Payment Hook — account.payment extension.

# # # # #     SRS §3.6: Full payment received → Bucket 4 → Paid.
# # # # #     SRS §4.3: Payment allowed only after bank acceptance.
# # # # #     SRS §6.2: Payment ALLOWED even when frozen.
# # # # #     SoD: Finance handles payment registration.

# # # # #     FIX from v0.2.0:
# # # # #     ─────────────────
# # # # #     Original code overrode account.move.line.reconcile() but:
# # # # #       1. Never called super().reconcile() — reconciliation never happened.
# # # # #       2. Used incorrect `self - line` logic to find invoice lines.
# # # # #       3. _post_reconcile_hook() does not exist in Odoo 19.

# # # # #     Correct approach: Override account.payment.action_post().
# # # # #     After payment is posted, Odoo auto-reconciles with the invoice.
# # # # #     reconciled_invoice_ids is available immediately after action_post().
# # # # #     We check bank_acceptance BEFORE allowing payment and detect paid state AFTER.
# # # # #     """

# # # # #     _inherit = 'account.payment'

# # # # #     # def action_post(self):
# # # # #     #     """
# # # # #     #     SoD: Finance posts payments.
# # # # #     #     Pre-check: Bank acceptance must be confirmed before payment (SRS §4.3).
# # # # #     #     Post-action: Detect fully paid invoices and move to 'paid' CLM stage.
# # # # #     #     Allowed even when frozen (SRS §6.2).
# # # # #     #     """
# # # # #     #     if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
# # # # #     #         raise AccessError(
# # # # #     #             "Only Finance can register and post payments."
# # # # #     #         )

# # # # #     #     # Pre-check: Bank acceptance required for all related sale orders
# # # # #     #     for payment in self.filtered(lambda p: p.partner_type == 'customer'):
# # # # #     #         self._clm_assert_bank_acceptance(payment)

# # # # #     #     result = super().action_post()

# # # # #     #     # Post-action: after Odoo reconciles payment with invoice,
# # # # #     #     # check if any invoice is now fully paid → move to CLM 'paid' stage.
# # # # #     #     # for payment in self.filtered(lambda p: p.partner_type == 'customer'):
# # # # #     #     #     self._clm_propagate_paid_state(payment)

# # # # #     #     for payment in self.filtered(lambda p: p.partner_type == 'customer'):
# # # # #     #         invoices = payment.reconciled_invoice_ids.filtered(
# # # # #     #             lambda m: m.move_type == 'out_invoice'
# # # # #     #         )

# # # # #     #         # Force recompute/refetch
# # # # #     #         invoices.invalidate_recordset()

# # # # #     #         paid_invoices = invoices.filtered(
# # # # #     #             lambda inv: inv.payment_state == 'paid'
# # # # #     #         )

# # # # #     #         if paid_invoices:
# # # # #     #             sale_orders = (
# # # # #     #                 paid_invoices.invoice_line_ids
# # # # #     #                 .mapped('sale_line_ids')
# # # # #     #                 .mapped('order_id')
# # # # #     #             )

# # # # #     #             sale_orders._clm_move_to_paid()

# # # # #     #             return result


# # # # #     def action_post(self):
# # # # #         """
# # # # #         SoD: Finance posts payments.
# # # # #         Pre-check: Bank acceptance must be confirmed before payment (SRS §4.3).
# # # # #         Post-action: Detect fully paid invoices and move to 'paid' CLM stage.
# # # # #         Allowed even when frozen (SRS §6.2).
# # # # #         """
# # # # #         if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
# # # # #             raise AccessError(
# # # # #                 "Only Finance can register and post payments."
# # # # #             )

# # # # #         # Pre-check: Bank acceptance required for all related sale orders
# # # # #         for payment in self.filtered(lambda p: p.partner_type == 'customer'):
# # # # #             self._clm_assert_bank_acceptance(payment)

# # # # #         result = super().action_post()

# # # # #         # Post-action: Odoo has now reconciled the payment with the invoice.
# # # # #         # Invalidate payment cache first so reconciled_invoice_ids reflects reality.
# # # # #         for payment in self.filtered(lambda p: p.partner_type == 'customer'):

# # # # #             # BUG FIX 2: Invalidate the PAYMENT's cache, not just invoices
# # # # #             payment.invalidate_recordset(['reconciled_invoice_ids'])

# # # # #             invoices = payment.reconciled_invoice_ids.filtered(
# # # # #                 lambda m: m.move_type == 'out_invoice'
# # # # #             )

# # # # #             if not invoices:
# # # # #                 continue

# # # # #             # BUG FIX 3: Include 'in_payment' — Odoo 19 posts to in_payment first
# # # # #             invoices.invalidate_recordset(['payment_state'])
# # # # #             paid_invoices = invoices.filtered(
# # # # #                 lambda inv: inv.payment_state in ('paid', 'in_payment')
# # # # #             )

# # # # #             if paid_invoices:
# # # # #                 sale_orders = (
# # # # #                     paid_invoices.invoice_line_ids
# # # # #                     .mapped('sale_line_ids')
# # # # #                     .mapped('order_id')
# # # # #                 )
# # # # #                 sale_orders._clm_move_to_paid()

# # # # #         # BUG FIX 1: return result is OUTSIDE the for loop
# # # # #         return result

# # # # #     def _clm_assert_bank_acceptance(self, payment):
# # # # #         """
# # # # #         Validates that all sale orders linked to this payment's reconciled
# # # # #         invoices have bank acceptance confirmed. Raises UserError if not.
# # # # #         SRS §4.3: Payment registration available only after bank acceptance.
# # # # #         """
# # # # #         # Find invoices that will be reconciled by this payment
# # # # #         # At pre-post stage, we look at payment lines' matched moves
# # # # #         linked_invoices = payment.invoice_ids  # invoices directly linked at payment wizard
# # # # #         if not linked_invoices:
# # # # #             return

# # # # #         for invoice in linked_invoices.filtered(
# # # # #             lambda m: m.move_type == 'out_invoice'
# # # # #         ):
# # # # #             sale_orders = (
# # # # #                 invoice.invoice_line_ids
# # # # #                 .mapped('sale_line_ids')
# # # # #                 .mapped('order_id')
# # # # #                 .filtered(lambda o: o.state != 'cancel' and o.clm_state != 'paid')
# # # # #             )
# # # # #             not_bank_accepted = sale_orders.filtered(lambda o: not o.clm_bank_acceptance)
# # # # #             if not_bank_accepted:
# # # # #                 refs = ', '.join(not_bank_accepted.mapped('name'))
# # # # #                 raise UserError(
# # # # #                     f"⛔  Payment Blocked — Bank Acceptance Required\n\n"
# # # # #                     f"The following orders have not received bank acceptance:\n"
# # # # #                     f"{refs}\n\n"
# # # # #                     f"Record bank acceptance before registering payment."
# # # # #                 )

# # # # #     def _clm_propagate_paid_state(self, payment):
# # # # #         """
# # # # #         After payment is posted and reconciled, find invoices that are now
# # # # #         fully paid and move their sale orders from Bucket 4 → Paid.
# # # # #         SRS §3.6.
# # # # #         """
# # # # #         # reconciled_invoice_ids is a computed field available after action_post()
# # # # #         for invoice in payment.reconciled_invoice_ids.filtered(
# # # # #             lambda m: (
# # # # #                 m.move_type == 'out_invoice'
# # # # #                 and m.payment_state in ('paid', 'in_payment')
# # # # #             )
# # # # #         ):
# # # # #             sale_orders = (
# # # # #                 invoice.invoice_line_ids
# # # # #                 .mapped('sale_line_ids')
# # # # #                 .mapped('order_id')
# # # # #             )
# # # # #             if sale_orders:
# # # # #                 sale_orders._clm_move_to_paid()

# # # # from odoo import models
# # # # from odoo.exceptions import UserError, AccessError


# # # # class AccountMoveExtended(models.Model):
# # # #     """
# # # #     Invoice Hook — account.move extension.
# # # #     SRS §3.3: Invoice posted → Bucket 1 → Bucket 2.
# # # #     """

# # # #     _inherit = 'account.move'

# # # #     def action_post(self):
# # # #         result = super().action_post()

# # # #         for move in self.filtered(
# # # #             lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
# # # #         ):
# # # #             sale_orders = (
# # # #                 move.invoice_line_ids
# # # #                 .mapped('sale_line_ids')
# # # #                 .mapped('order_id')
# # # #             )
# # # #             if sale_orders:
# # # #                 sale_orders._clm_move_to_bucket2()

# # # #         return result


# # # # class AccountPaymentExtended(models.Model):
# # # #     """
# # # #     Payment Hook — account.payment extension.
# # # #     SRS §3.6: Full payment → Bucket 4 → Paid.
# # # #     """

# # # #     _inherit = 'account.payment'

# # # #     def action_post(self):
# # # #         """
# # # #         Odoo 19 Fix:
# # # #         ─────────────
# # # #         reconciled_invoice_ids is empty immediately after super().action_post()
# # # #         because reconciliation is now a deferred ORM flush operation in Odoo 19.

# # # #         Correct approach:
# # # #           1. Capture invoice_ids (direct stored M2M) BEFORE super() — always populated.
# # # #           2. Call flush_all() AFTER super() — forces Odoo to complete reconciliation
# # # #              and recompute payment_state on all affected invoices.
# # # #           3. Browse invoices fresh from DB using stored IDs.
# # # #           4. Check payment_state AFTER flush.
# # # #         """
# # # #         if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
# # # #             raise AccessError("Only Finance can register and post payments.")

# # # #         customer_payments = self.filtered(lambda p: p.partner_type == 'customer')

# # # #         # Pre-check: bank acceptance required before payment
# # # #         for payment in customer_payments:
# # # #             self._clm_assert_bank_acceptance(payment)

# # # #         # ── STEP 1: Capture invoice IDs BEFORE posting ──────────────────────
# # # #         # invoice_ids is a direct stored Many2many set by the payment wizard.
# # # #         # It is reliable at this point. reconciled_invoice_ids is NOT — it is
# # # #         # a computed field that requires reconciliation to complete first.
# # # #         payment_invoice_map = {
# # # #             p.id: p.invoice_ids.filtered(
# # # #                 lambda m: m.move_type == 'out_invoice'
# # # #             ).ids
# # # #             for p in customer_payments
# # # #         }
# # # #         print("3333333333333333333333333333333333333333333333333333333333333333333333333333333333333")
# # # #         result = super().action_post()

# # # #         # ── STEP 2: flush_all() — Critical for Odoo 19 ──────────────────────
# # # #         # Forces completion of all pending ORM computations, including:
# # # #         #   - journal entry reconciliation
# # # #         #   - payment_state recompute on account.move
# # # #         #   - amount_residual recompute
# # # #         # Without this, payment_state is still 'not_paid' in the ORM cache.
# # # #         self.env.flush_all()

# # # #         # ── STEP 3: Check payment_state on captured invoices ─────────────────
# # # #         for payment in customer_payments:
# # # #             invoice_ids = payment_invoice_map.get(payment.id, [])
# # # #             if not invoice_ids:
# # # #                 continue

# # # #             # Browse fresh — bypasses stale ORM cache entirely
# # # #             invoices = self.env['account.move'].browse(invoice_ids)

# # # #             # Explicit invalidation as a safety net on top of flush_all()
# # # #             invoices.invalidate_recordset(['payment_state', 'amount_residual'])

# # # #             paid_invoices = invoices.filtered(
# # # #                 lambda inv: inv.payment_state in ('paid', 'in_payment')
# # # #             )

# # # #             if not paid_invoices:
# # # #                 continue

# # # #             sale_orders = (
# # # #                 paid_invoices.invoice_line_ids
# # # #                 .mapped('sale_line_ids')
# # # #                 .mapped('order_id')
# # # #             )
# # # #             if sale_orders:
# # # #                 sale_orders._clm_move_to_paid()

# # # #         return result

# # # #     def _clm_assert_bank_acceptance(self, payment):
# # # #         """
# # # #         SRS §4.3: Payment blocked until bank acceptance confirmed.
# # # #         Checks invoice_ids (direct link, available pre-post).
# # # #         """
# # # #         linked_invoices = payment.invoice_ids
# # # #         if not linked_invoices:
# # # #             return

# # # #         for invoice in linked_invoices.filtered(lambda m: m.move_type == 'out_invoice'):
# # # #             sale_orders = (
# # # #                 invoice.invoice_line_ids
# # # #                 .mapped('sale_line_ids')
# # # #                 .mapped('order_id')
# # # #                 .filtered(lambda o: o.state != 'cancel' and o.clm_state != 'paid')
# # # #             )
# # # #             not_bank_accepted = sale_orders.filtered(lambda o: not o.clm_bank_acceptance)
# # # #             if not_bank_accepted:
# # # #                 refs = ', '.join(not_bank_accepted.mapped('name'))
# # # #                 raise UserError(
# # # #                     f"⛔  Payment Blocked — Bank Acceptance Required\n\n"
# # # #                     f"The following orders have not received bank acceptance:\n"
# # # #                     f"{refs}\n\n"
# # # #                     f"Record bank acceptance before registering payment."
# # # #                 )

# # # from odoo import models
# # # from odoo.exceptions import UserError, AccessError


# # # class AccountMoveExtended(models.Model):
# # #     """
# # #     Invoice Hook — account.move extension.
# # #     SRS §3.3: Invoice posted → Bucket 1 → Bucket 2.
# # #     """

# # #     _inherit = 'account.move'

# # #     def action_post(self):
# # #         result = super().action_post()

# # #         for move in self.filtered(
# # #             lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
# # #         ):
# # #             sale_orders = (
# # #                 move.invoice_line_ids
# # #                 .mapped('sale_line_ids')
# # #                 .mapped('order_id')
# # #             )
# # #             if sale_orders:
# # #                 sale_orders._clm_move_to_bucket2()

# # #         return result


# # # class AccountPaymentExtended(models.Model):
# # #     """
# # #     Payment Hook — account.payment extension.
# # #     SRS §3.6: Full payment → Bucket 4 → Paid.

# # #     ── Odoo 19 Critical Fix ────────────────────────────────────────────────────

# # #     ROOT CAUSE of the bucket4 → paid bug:
# # #       The original code pre-captured `payment.invoice_ids` before super().action_post().
# # #       The comment claimed this was "a direct stored Many2many set by the payment wizard".
# # #       THIS IS WRONG. `account.payment.invoice_ids` was REMOVED in Odoo 16+ and does NOT
# # #       exist in Odoo 19. Accessing it returns an empty recordset every time, so
# # #       `payment_invoice_map` was always `{payment_id: []}`, the `if not invoice_ids: continue`
# # #       branch always fired, and `_clm_move_to_paid()` was NEVER called.

# # #     Correct approach (Odoo 19):
# # #       1. Run SoD check and bank acceptance pre-check.
# # #       2. Call super().action_post() — posts the journal entry and triggers auto-reconciliation.
# # #       3. Call flush_all() — forces the ORM to complete all deferred computations:
# # #            - account.partial.reconcile creation
# # #            - payment_state recompute on account.move
# # #            - amount_residual recompute
# # #          Without flush_all(), payment_state is still 'not_paid' in the ORM cache.
# # #       4. Invalidate reconciled_invoice_ids cache on each payment record.
# # #       5. Read payment.reconciled_invoice_ids — now populated and accurate.
# # #       6. Filter for paid/in_payment invoices and propagate CLM stage.

# # #     Bank acceptance pre-check (Odoo 19):
# # #       account.payment has no stored link to invoices before posting.
# # #       Discover the invoices being paid via:
# # #         - context['active_ids'] when triggered from the Register Payment wizard
# # #           (account.payment.register passes the invoice context through to action_post)
# # #         - Fallback: partner's open posted invoices
# # #     ────────────────────────────────────────────────────────────────────────────
# # #     """

# # #     _inherit = 'account.payment'

# # #     def action_post(self):
# # #         if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
# # #             raise AccessError("Only Finance can register and post payments.")
# # #         print("FinnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnanccccccccccccccccEEEEEEEEEEEEEEEEEEEee")
# # #         customer_payments = self.filtered(lambda p: p.partner_type == 'customer')

# # #         # ── PRE-CHECK: Bank acceptance required before any payment ───────────
# # #         # for payment in customer_payments:
# # #         #     self._clm_assert_bank_acceptance(payment)

# # #         # ── POST: Journal entry is posted and auto-reconciled by Odoo ────────
# # #         result = super().action_post()

# # #         # ── FLUSH: Forces ORM to complete all deferred reconciliation OPs ────
# # #         # This recomputes payment_state / amount_residual on affected invoices.
# # #         # Without this, reconciled_invoice_ids is empty and payment_state is stale.
# # #         self.env.flush_all()

# # #         # ── DETECT PAID INVOICES and propagate CLM stage ─────────────────────
# # #         for payment in customer_payments:
# # #             # Invalidate the computed field cache — bypass any stale ORM value.
# # #             payment.invalidate_recordset(['reconciled_invoice_ids'])

# # #             invoices = payment.reconciled_invoice_ids.filtered(
# # #                 lambda m: m.move_type == 'out_invoice'
# # #             )
# # #             if not invoices:
# # #                 continue

# # #             # Invalidate invoice-level computed fields before reading
# # #             invoices.invalidate_recordset(['payment_state', 'amount_residual'])

# # #             # 'in_payment' = payment posted but bank not yet processed (still counts)
# # #             paid_invoices = invoices.filtered(
# # #                 lambda inv: inv.payment_state in ('paid', 'in_payment')
# # #             )
# # #             if not paid_invoices:
# # #                 continue
# # #             print("####################################################################################")
# # #             sale_orders = (
# # #                 paid_invoices.invoice_line_ids
# # #                 .mapped('sale_line_ids')
# # #                 .mapped('order_id')
# # #             )
# # #             if sale_orders:
# # #                 sale_orders._clm_move_to_paid()

# # #         return result

# # #     def _clm_assert_bank_acceptance(self, payment):
# # #         """
# # #         Validates that all sale orders linked to the invoices being paid have
# # #         bank acceptance recorded. Raises UserError if any are missing.
# # #         SRS §4.3: Payment registration blocked until bank acceptance confirmed.

# # #         Invoice discovery (Odoo 19):
# # #           account.payment has no stored invoice_ids field. Two strategies:

# # #           Strategy 1 — Context active_ids (primary):
# # #             When the user clicks "Register Payment" from an invoice,
# # #             account.payment.register passes active_model='account.move' and
# # #             active_ids=[invoice.id] in context. This context propagates through
# # #             _create_payments() → payment.action_post(), so it is available here.

# # #           Strategy 2 — Partner open invoices (fallback):
# # #             When context is absent (e.g. payment created programmatically),
# # #             find all open posted invoices for this payment's partner.
# # #         """
# # #         ctx = self.env.context
# # #         if ctx.get('active_model') == 'account.move' and ctx.get('active_ids'):
# # #             # Primary: targeted check on the invoices being registered
# # #             linked_invoices = self.env['account.move'].browse(
# # #                 ctx['active_ids']
# # #             ).filtered(lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
# # #         else:
# # #             # Fallback: check all open invoices for this partner
# # #             linked_invoices = self.env['account.move'].search([
# # #                 ('partner_id', '=', payment.partner_id.id),
# # #                 ('move_type', '=', 'out_invoice'),
# # #                 ('payment_state', 'in', ('not_paid', 'partial')),
# # #                 ('state', '=', 'posted'),
# # #             ])

# # #         if not linked_invoices:
# # #             return

# # #         for invoice in linked_invoices:
# # #             sale_orders = (
# # #                 invoice.invoice_line_ids
# # #                 .mapped('sale_line_ids')
# # #                 .mapped('order_id')
# # #                 .filtered(lambda o: o.state != 'cancel' and o.clm_state != 'paid')
# # #             )
# # #             not_bank_accepted = sale_orders.filtered(lambda o: not o.clm_bank_acceptance)
# # #             if not_bank_accepted:
# # #                 refs = ', '.join(not_bank_accepted.mapped('name'))
# # #                 raise UserError(
# # #                     "⛔  Payment Blocked — Bank Acceptance Required\n\n"
# # #                     "The following orders have not received bank acceptance:\n"
# # #                     f"{refs}\n\n"
# # #                     "Record bank acceptance on the sale order before registering payment."
# # #                 )

# # from odoo import models
# # from odoo.exceptions import UserError, AccessError


# # class AccountMoveExtended(models.Model):
# #     """
# #     Invoice Hook — account.move extension.
# #     SRS §3.3: Invoice posted → Bucket 1 → Bucket 2.
# #     """

# #     _inherit = 'account.move'

# #     def action_post(self):
# #         result = super().action_post()

# #         for move in self.filtered(
# #             lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
# #         ):
# #             sale_orders = (
# #                 move.invoice_line_ids
# #                 .mapped('sale_line_ids')
# #                 .mapped('order_id')
# #             )
# #             # if sale_orders:
# #             #     sale_orders._clm_move_to_bucket2()

# #         return result
    
# #     def action_register_payment(self):
# #         """
# #         SoD: Only Finance can register payments.
# #         Allowed even when customer is frozen (SRS §6.2).
# #         """
# #         if not self.env.user.has_group('zencore_groups.group_zencore_clm_finance'):
# #             raise AccessError(
# #                 "Only Finance can register payments for invoices."
# #             )
# #         for move in self.filtered(
# #             lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
# #         ):
# #             sale_orders = (
# #                 move.invoice_line_ids
# #                 .mapped('sale_line_ids')
# #                 .mapped('order_id')
# #             )
# #             if sale_orders.clm_state != 'bucket4':
# #                 raise UserError(
# #                     "⛔  Payment Registration Blocked — Bank Acceptance Required\n\n"
# #                     "Payment can only be registered after Bank Acceptance is confirmed\n"
# #                     "and the order reaches Bucket 4.\n\n"
# #                     "Blocked Orders:\n"
# #                     "Resolution:\n"
# #                     "  1. Open the sale order.\n"
# #                     "  2. Click '🏦 Bank Acceptance' button (CCM or Finance).\n"
# #                     "  3. Return here to register payment."
# #                 )
                
# #         return super().action_register_payment()


# # class AccountPaymentExtended(models.Model):
# #     """
# #     Payment Hook — account.payment extension.
# #     SRS §3.6: Full payment → Bucket 4 → Paid.

# #     ── Odoo 19 Architecture Notes ──────────────────────────────────────────────

# #     Why flush_all() is required:
# #       In Odoo 19, journal entry reconciliation (account.partial.reconcile creation)
# #       and the subsequent recompute of payment_state / amount_residual on account.move
# #       are deferred ORM operations. They are enqueued during super().action_post()
# #       but NOT flushed to the DB yet. Without flush_all(), reconciled_invoice_ids
# #       is empty and payment_state is still 'not_paid' in the ORM cache.
# #       flush_all() forces all pending writes and recomputes to complete before we read.

# #     Why invalidate_recordset() after flush_all():
# #       flush_all() writes to DB but the ORM in-memory cache may still hold stale
# #       values for computed fields. invalidate_recordset() clears the in-memory cache
# #       on the specific record, forcing the next field access to re-read from DB.

# #     ── BUG #6 FIX: Finance SoD check scope ─────────────────────────────────────

# #     PROBLEM (original code):
# #       The Finance group check used a hard raise with no scope guard.
# #       Odoo 19 automated processes (bank statement import, auto-reconcile scheduler,
# #       SEPA payment batches) call account.payment.action_post() internally.
# #       These processes do NOT run as a Finance user — they run as OdooBot or the
# #       technical user. The hard raise blocked all automated payment posting.

# #     FIX:
# #       Guard the check with `not self.env.su` (True when called via sudo()) AND
# #       `not self.env.context.get('clm_skip_sod_check')` for internal callers that
# #       need an explicit opt-out. The check only fires for real interactive sessions
# #       where a named user is actually posting the payment.

# #     ── Why reconciled_invoice_ids works here (not invoice_ids) ─────────────────

# #       account.payment.invoice_ids was REMOVED in Odoo 16.
# #       The correct Odoo 19 field is reconciled_invoice_ids — a computed field
# #       populated AFTER the payment journal entry is reconciled with the invoice
# #       journal entry. It is accurate only after flush_all() + invalidate_recordset().
# #     ────────────────────────────────────────────────────────────────────────────
# #     """

# #     _inherit = 'account.payment'


# #     def action_validate(self):
# #         # Call original method
# #         res = super().action_validate()

# #         for payment in self:
# #             # Find related invoices from payment
# #             invoices = payment.reconciled_invoice_ids

# #             # Get related sale orders from invoice lines
# #             sale_orders = invoices.mapped('invoice_line_ids.sale_line_ids.order_id')

# #             # Update bucket 4 stage
# #             sale_orders._clm_move_to_paid()

# #         return res

# #     def action_post(self):
# #         """
# #         SoD: Finance posts payments (interactive sessions only).
# #         Post-action: detect fully paid invoices and move CLM stage to 'paid'.
# #         Allowed even when customer is frozen (SRS §6.2).
# #         """
# #         # ── BUG #6 FIX: Scope the SoD check ────────────────────────────────
# #         # Only enforce for real user sessions (not sudo, not automated flows).
# #         # self.env.su  = True when called via sudo() — automated reconciliation
# #         # clm_skip_sod_check = explicit opt-out for internal callers
# #         if not self.env.su and not self.env.context.get('clm_skip_sod_check'):
# #             customer_payments = self.filtered(lambda p: p.partner_type == 'customer')
# #             if customer_payments:
# #                 if not self.env.user.has_group('zencore_groups.group_zencore_clm_finance'):
# #                     raise AccessError(
# #                         "Only Finance can register and post customer payments."
# #                     )

# #         customer_payments = self.filtered(lambda p: p.partner_type == 'customer')

# #         # ── POST: Odoo posts the journal entry and auto-reconciles ───────────
# #         result = super().action_post()

# #         # ── FLUSH: Force all deferred ORM operations to complete ─────────────
# #         # This recomputes payment_state and amount_residual on affected invoices.
# #         # Without this, reconciled_invoice_ids is empty and payment_state is stale.
# #         self.env.flush_all()

# #         # ── DETECT PAID INVOICES and propagate CLM stage ─────────────────────
# #         for payment in customer_payments:
# #             # Clear in-memory ORM cache so next read hits DB (post-flush values)
# #             payment.invalidate_recordset(['reconciled_invoice_ids'])

# #             invoices = payment.reconciled_invoice_ids.filtered(
# #                 lambda m: m.move_type == 'out_invoice'
# #             )
# #             if not invoices:
# #                 continue

# #             invoices.invalidate_recordset(['payment_state', 'amount_residual'])

# #             # 'in_payment' = posted but bank not yet processed — still counts.
# #             # The order moves to 'paid' at this point; the bank clearing is
# #             # tracked separately by the bank acceptance flag.
# #             paid_invoices = invoices.filtered(
# #                 lambda inv: inv.payment_state in ('paid', 'in_payment')
# #             )
# #             if not paid_invoices:
# #                 continue

# #             # invoice_line_ids.sale_line_ids is populated when invoices are
# #             # created from sale orders via the standard Odoo flow (_create_invoices).
# #             # Manually created invoices may not have sale_line_ids — in that case
# #             # _clm_move_to_paid() finds no matching bucket4 orders and logs a
# #             # diagnostic chatter note on each order explaining the skip.
# #             sale_orders = (
# #                 paid_invoices.invoice_line_ids
# #                 .mapped('sale_line_ids')
# #                 .mapped('order_id')
# #             )
# #             if sale_orders:
# #                 sale_orders._clm_move_to_paid()

# #         return result

# #     def _clm_assert_bank_acceptance(self, payment):
# #         """
# #         Validates that all sale orders linked to the invoices being paid have
# #         bank acceptance recorded. Raises UserError if any are missing.
# #         SRS §4.3: Payment registration blocked until bank acceptance confirmed.

# #         Invoice discovery (Odoo 19):
# #           account.payment has no stored invoice_ids field. Two strategies:

# #           Strategy 1 — Context active_ids (primary):
# #             When the user clicks "Register Payment" from an invoice,
# #             account.payment.register passes active_model='account.move' and
# #             active_ids=[invoice.id] in context. This context propagates through
# #             _create_payments() → payment.action_post(), so it is available here.

# #           Strategy 2 — Partner open invoices (fallback):
# #             When context is absent (e.g. payment created programmatically),
# #             find all open posted invoices for this payment's partner.
# #         """
# #         ctx = self.env.context
# #         if ctx.get('active_model') == 'account.move' and ctx.get('active_ids'):
# #             linked_invoices = self.env['account.move'].browse(
# #                 ctx['active_ids']
# #             ).filtered(lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
# #         else:
# #             linked_invoices = self.env['account.move'].search([
# #                 ('partner_id', '=', payment.partner_id.id),
# #                 ('move_type', '=', 'out_invoice'),
# #                 ('payment_state', 'in', ('not_paid', 'partial')),
# #                 ('state', '=', 'posted'),
# #             ])

# #         if not linked_invoices:
# #             return

# #         for invoice in linked_invoices:
# #             sale_orders = (
# #                 invoice.invoice_line_ids
# #                 .mapped('sale_line_ids')
# #                 .mapped('order_id')
# #                 .filtered(lambda o: o.state != 'cancel' and o.clm_state != 'paid')
# #             )
# #             not_bank_accepted = sale_orders.filtered(lambda o: not o.clm_bank_acceptance)
# #             if not_bank_accepted:
# #                 refs = ', '.join(not_bank_accepted.mapped('name'))
# #                 raise UserError(
# #                     "⛔  Payment Blocked — Bank Acceptance Required\n\n"
# #                     "The following orders have not received bank acceptance:\n"
# #                     f"{refs}\n\n"
# #                     "Record bank acceptance on the sale order before registering payment."
# #                 )
# # # class AccountPaymentRegisterExtended(models.TransientModel):
# # #     """
# # #     Extension of account.payment.register to enforce SoD and bank acceptance checks at the point of payment registration.
# # #     This ensures that even if someone bypasses action_post() directly, they still cannot register a payment without passing the necessary checks.
# # #     """
    
# # #     _inherit = 'account.payment.register'

# # #     def _create_payments(self):
# # #         """
# # #         Override the payment creation process to include SoD and bank acceptance checks before any payment is created.
# # #         This is a critical extension point because it is the entry point for payment registration from the invoice form.
# # #         """
# # #         # SoD Check: Only Finance can register payments
# # #         if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
# # #             raise AccessError(
# # #                 "Only Finance can register payments for invoices."
# # #             )

# # #         # Bank Acceptance Check: Ensure all related sale orders have bank acceptance before allowing payment registration
# # #         for move in self.invoice_ids:
# # #             if move.move_type == 'out_invoice' and move.state == 'posted':
# # #                 sale_orders = (
# # #                     move.invoice_line_ids
# # #                     .mapped('sale_line_ids')
# # #                     .mapped('order_id')
# # #                 )
# # #                 if sale_orders.filtered(lambda o: o.clm_state != 'paid' and not o.clm_bank_acceptance):
# # #                     refs = ', '.join(sale_orders.mapped('name'))
# # #                     raise UserError(
# # #                         "⛔  Payment Registration Blocked — Bank Acceptance Required\n\n"
# # #                         "The following orders have not received bank acceptance:\n"
# # #                         f"{refs}\n\n"
# # #                         "Record bank acceptance on the sale order before registering payment."
# # #                     )

# # #         # If all checks pass, proceed with the original payment creation logic
# # #         return super()._create_payments()

# from odoo import models, fields, api
# from odoo.exceptions import UserError, AccessError
# from markupsafe import Markup


# class AccountMoveExtended(models.Model):
#     """
#     Invoice Hook — account.move extension.

#     ── Per-Invoice CLM Acceptance (SRS §4) ─────────────────────────────────────
#     SRS §4.1/§4.2 explicitly states:
#       "A field named Customer Acceptance / Bank Acceptance must exist on
#        Customer Invoice. Managed per Invoice."

#     These fields were previously on sale.order — that was WRONG.
#     They are now correctly on account.move (the Customer Invoice).

#     Bucket exposure transitions driven by these fields (partner balances are
#     non-stored computes that read invoice state directly — no explicit
#     "move to bucket X" calls needed):

#       Invoice posted                → Bucket 2  (no customer acceptance yet)
#       clm_customer_acceptance=True  → Bucket 3  (balance recomputes automatically)
#       clm_bank_acceptance=True      → Bucket 4  (balance recomputes automatically)
#       Due date passes               → Bucket 5  (SQL in partner compute uses CURRENT_DATE)
#       Payment received              → Bucket reduces from 4 or 5

#     ── SO Operational Stage Hooks ──────────────────────────────────────────────
#     action_post()        → calls SO._clm_update_invoice_stage()
#     AccountPaymentExtended.action_post() → calls SO._clm_update_payment_stage()

#     ── SoD (SRS §10) ──────────────────────────────────────────────────────────
#       Invoice post        : TDO
#       Customer acceptance : CCM or Salesperson
#       Bank acceptance     : CCM or Finance
#       Payment register    : Finance
#     """

#     _inherit = 'account.move'

#     # ─────────────────────────────────────────────────────────────────────────
#     # PER-INVOICE CLM ACCEPTANCE FIELDS  (SRS §4.1 / §4.2)
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_customer_acceptance = fields.Boolean(
#         string='Customer Acceptance',
#         default=False,
#         tracking=True,
#         copy=False,
#         help=(
#             'SRS §4.1 — Hidden before posting; visible after invoice is posted.\n'
#             'Triggers: invoice exposure moves from Bucket 2 → Bucket 3.'
#         ),
#     )

#     clm_bank_acceptance = fields.Boolean(
#         string='Bank Acceptance',
#         default=False,
#         tracking=True,
#         copy=False,
#         help=(
#             'SRS §4.2 — Visible only after Customer Acceptance is confirmed.\n'
#             'Triggers: invoice exposure moves from Bucket 3 → Bucket 4.'
#         ),
#     )

#     # ── Visibility Compute Fields ─────────────────────────────────────────────

#     clm_show_customer_acceptance_btn = fields.Boolean(
#         compute='_compute_clm_invoice_visibility',
#         string='Show Customer Acceptance Button',
#     )
#     clm_show_bank_acceptance_btn = fields.Boolean(
#         compute='_compute_clm_invoice_visibility',
#         string='Show Bank Acceptance Button',
#     )
#     clm_payment_locked = fields.Boolean(
#         compute='_compute_clm_invoice_visibility',
#         string='Payment Locked (Bank Acceptance Required)',
#     )

#     @api.depends(
#         'state',
#         'move_type',
#         'clm_customer_acceptance',
#         'clm_bank_acceptance',
#         'payment_state',
#     )
#     def _compute_clm_invoice_visibility(self):
#         for move in self:
#             if move.move_type != 'out_invoice' or move.state != 'posted':
#                 move.clm_show_customer_acceptance_btn = False
#                 move.clm_show_bank_acceptance_btn = False
#                 move.clm_payment_locked = False
#                 continue

#             is_outstanding = move.payment_state not in ('paid', 'in_payment', 'reversed')

#             # SRS §4.1: Customer acceptance button — after posting, before accepted
#             move.clm_show_customer_acceptance_btn = (
#                 not move.clm_customer_acceptance and is_outstanding
#             )
#             # SRS §4.2: Bank acceptance button — after customer accepted, before bank
#             move.clm_show_bank_acceptance_btn = (
#                 move.clm_customer_acceptance
#                 and not move.clm_bank_acceptance
#                 and is_outstanding
#             )
#             # SRS §4.3: Payment is locked until bank acceptance is confirmed
#             move.clm_payment_locked = is_outstanding and not move.clm_bank_acceptance

#     # ─────────────────────────────────────────────────────────────────────────
#     # ACCEPTANCE ACTIONS  (SRS §4.1 / §4.2)
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_clm_customer_acceptance(self):
#         """
#         Records customer acceptance on this invoice.
#         SRS §4.1: Invoice exposure moves Bucket 2 → Bucket 3.
#         SoD: CCM or Salesperson.
#         Allowed even when customer is frozen (SRS §6.2).
#         """
#         if not (
#             self.env.user.has_group('zencore_groups.group_zencore_clm_ccm')
#             or self.env.user.has_group('zencore_groups.group_zencore_clm_salesperson')
#         ):
#             raise AccessError(
#                 "Only CCM or Salesperson can record Customer Acceptance on invoices.\n"
#                 "SRS §10 — Separation of Duties."
#             )

#         for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
#             if move.state != 'posted':
#                 raise UserError(
#                     f"Invoice {move.name} must be in Posted state before recording "
#                     f"Customer Acceptance. Current state: {move.state}."
#                 )
#             if move.clm_customer_acceptance:
#                 raise UserError(
#                     f"Customer Acceptance is already recorded on invoice {move.name}."
#                 )

#             move.write({'clm_customer_acceptance': True})
#             move.message_post(
#                 body=Markup(
#                     "<b>✔ Customer Acceptance Recorded</b><br/>"
#                     "Invoice     : {inv}<br/>"
#                     "Outstanding : {sym} {amt:,.2f}<br/>"
#                     "Recorded by : {user}<br/>"
#                     "<em>Effect: Invoice exposure transitions Bucket 2 → Bucket 3</em>"
#                 ).format(
#                     inv=move.name or '—',
#                     sym=move.currency_id.symbol or '',
#                     amt=move.amount_residual,
#                     user=self.env.user.name,
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#     def action_clm_bank_acceptance(self):
#         """
#         Records bank acceptance on this invoice.
#         SRS §4.2: Invoice exposure moves Bucket 3 → Bucket 4.
#         SoD: CCM or Finance.
#         Allowed even when customer is frozen (SRS §6.2).
#         """
#         if not (
#             self.env.user.has_group('zencore_groups.group_zencore_clm_ccm')
#             or self.env.user.has_group('zencore_groups.group_zencore_clm_finance')
#         ):
#             raise AccessError(
#                 "Only CCM or Finance can record Bank Acceptance on invoices.\n"
#                 "SRS §10 — Separation of Duties."
#             )

#         for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
#             if not move.clm_customer_acceptance:
#                 raise UserError(
#                     f"Customer Acceptance must be recorded first on invoice {move.name}.\n"
#                     "SRS §4.2: Bank Acceptance is only available after Customer Acceptance."
#                 )
#             if move.clm_bank_acceptance:
#                 raise UserError(
#                     f"Bank Acceptance is already recorded on invoice {move.name}."
#                 )

#             move.write({'clm_bank_acceptance': True})
#             move.message_post(
#                 body=Markup(
#                     "<b>🏦 Bank Acceptance Recorded</b><br/>"
#                     "Invoice     : {inv}<br/>"
#                     "Outstanding : {sym} {amt:,.2f}<br/>"
#                     "Recorded by : {user}<br/>"
#                     "<em>Effect: Invoice exposure transitions Bucket 3 → Bucket 4</em>"
#                 ).format(
#                     inv=move.name or '—',
#                     sym=move.currency_id.symbol or '',
#                     amt=move.amount_residual,
#                     user=self.env.user.name,
#                 ),
#                 subtype_xmlid='mail.mt_note',
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # INVOICE POST HOOK  (SRS §3.3)
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_post(self):
#         """
#         SRS §3.3: Invoice posted → invoice automatically enters Bucket 2
#         (partner balance recompute reads invoice state via SQL).

#         SO operational stage updated: → partially_invoiced or fully_invoiced.
#         Allowed even when customer is frozen (SRS §6.2).
#         """
#         result = super().action_post()

#         for move in self.filtered(
#             lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
#         ):
#             sale_orders = (
#                 move.invoice_line_ids
#                 .mapped('sale_line_ids')
#                 .mapped('order_id')
#                 .filtered(lambda o: o.state not in ('cancel', 'draft'))
#             )
#             if sale_orders:
#                 sale_orders._clm_update_invoice_stage()

#         return result

#     # ─────────────────────────────────────────────────────────────────────────
#     # PAYMENT REGISTRATION GATE  (SRS §4.3 / §6.2)
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_register_payment(self):
#         """
#         SRS §4.3: Bank acceptance is required before payment registration.
#         SoD: Only Finance can register payments.
#         Allowed even when customer is frozen (SRS §6.2).
#         """
#         if not self.env.user.has_group('zencore_groups.group_zencore_clm_finance'):
#             raise AccessError(
#                 "Only Finance can register payments for customer invoices.\n"
#                 "SRS §10 — Separation of Duties."
#             )

#         # Validate bank acceptance on each invoice being paid
#         # for move in self.filtered(
#         #     lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
#         # ):
#         #     if not move.clm_bank_acceptance:
#         #         raise UserError(
#         #             "⛔  Payment Blocked — Bank Acceptance Required\n\n"
#         #             f"Invoice      : {move.name}\n"
#         #             f"Customer     : {move.partner_id.name}\n"
#         #             f"Outstanding  : {move.currency_id.symbol} {move.amount_residual:,.2f}\n\n"
#         #             "SRS §4.3: Payment registration is only available after Bank Acceptance.\n\n"
#         #             "Resolution:\n"
#         #             "  1. Ensure Customer Acceptance is recorded on this invoice.\n"
#         #             "  2. Click '🏦 Bank Acceptance' button on the invoice.\n"
#         #             "  3. Return here to register payment."
#         #         )

#         return super().action_register_payment()


# class AccountPaymentExtended(models.Model):
#     """
#     Payment Hook — account.payment extension.

#     SRS §3.6: Payment received → reduces exposure from Bucket 4 (non-overdue)
#               or Bucket 5 (overdue). Partner balance recomputes automatically
#               from amount_residual on invoices — no explicit bucket move needed.

#     SO operational stage: payment detected → _clm_update_payment_stage().

#     ── Odoo 19 Architecture: Why flush_all() + invalidate_recordset() ───────────
#     Odoo 19 defers reconciliation OPs and computed field recomputes until the
#     next DB flush. Immediately after super().action_post():
#       - account.partial.reconcile records may not yet be written
#       - payment_state on account.move is still 'not_paid' in ORM cache
#       - reconciled_invoice_ids is empty

#     flush_all() → forces all pending writes and recomputes to DB.
#     invalidate_recordset() → clears in-memory ORM cache so next read hits DB.

#     ── SoD check scope: interactive sessions only ───────────────────────────────
#     Automated flows (bank statement import, SEPA batches, scheduled auto-reconcile)
#     call action_post() as OdooBot/technical user. A hard raise would block them.
#     Guard: `not self.env.su and not ctx.get('clm_skip_sod_check')`.
#     """

#     _inherit = 'account.payment'

#     def action_post(self):
#         """
#         SoD: Finance posts customer payments (interactive sessions only).
#         Post-action: detect paid invoices → update SO operational stage.
#         """
#         if not self.env.su and not self.env.context.get('clm_skip_sod_check'):
#             customer_payments = self.filtered(lambda p: p.partner_type == 'customer')
#             if customer_payments:
#                 if not self.env.user.has_group('zencore_groups.group_zencore_clm_finance'):
#                     raise AccessError(
#                         "Only Finance can register and post customer payments."
#                     )

#         customer_payments = self.filtered(lambda p: p.partner_type == 'customer')

#         result = super().action_post()

#         # ── FLUSH: forces deferred reconciliation/recompute OPs to complete ──
#         self.env.flush_all()

#         for payment in customer_payments:
#             # Clear stale ORM cache — must read from DB after flush_all()
#             payment.invalidate_recordset(['reconciled_invoice_ids'])

#             invoices = payment.reconciled_invoice_ids.filtered(
#                 lambda m: m.move_type == 'out_invoice'
#             )
#             if not invoices:
#                 continue

#             invoices.invalidate_recordset(['payment_state', 'amount_residual'])

#             sale_orders = (
#                 invoices.invoice_line_ids
#                 .mapped('sale_line_ids')
#                 .mapped('order_id')
#                 .filtered(lambda o: o.state not in ('cancel', 'draft'))
#             )
#             if sale_orders:
#                 sale_orders._clm_update_payment_stage()

#         return result

from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError
from markupsafe import Markup


class AccountMoveExtended(models.Model):
    """
    Invoice Hook — account.move extension.

    ── Per-Invoice CLM Acceptance (SRS §4) ─────────────────────────────────────
    SRS §4.1/§4.2: Customer Acceptance and Bank Acceptance live on the invoice
    (account.move), not on sale.order. This is the correct design.

    Bucket exposure transitions (partner balances are non-stored SQL computes
    that read invoice state directly — no explicit "move to bucket X" calls):

      Invoice posted                → balance enters Bucket 2
      clm_customer_acceptance=True  → balance moves Bucket 2 → 3 (recomputed)
      clm_bank_acceptance=True      → balance moves Bucket 3 → 4 (recomputed)
      invoice_date_due < today      → balance moves Bucket 4 → 5 (SQL CURRENT_DATE)
      Payment received              → balance reduces from Bucket 4 or 5

    ── SoD (SRS §10) ───────────────────────────────────────────────────────────
      Invoice post         : TDO
      Customer acceptance  : CCM or Salesperson
      Bank acceptance      : CCM or Finance
      Payment registration : Finance
    """

    _inherit = 'account.move'

    # ─────────────────────────────────────────────────────────────────────────
    # PER-INVOICE CLM ACCEPTANCE FIELDS  (SRS §4.1 / §4.2)
    # ─────────────────────────────────────────────────────────────────────────

    clm_customer_acceptance = fields.Boolean(
        string='Customer Acceptance',
        default=False,
        tracking=True,
        copy=False,
        help=(
            'SRS §4.1 — Hidden before posting; visible after invoice is posted.\n'
            'Records that the customer has accepted goods/services.\n'
            'Effect: invoice outstanding balance transitions Bucket 2 → Bucket 3.'
        ),
    )

    clm_bank_acceptance = fields.Boolean(
        string='Bank Acceptance',
        default=False,
        tracking=True,
        copy=False,
        help=(
            'SRS §4.2 — Visible only after Customer Acceptance is confirmed.\n'
            'Records that the bank has processed the LC/acceptance documents.\n'
            'Effect: invoice outstanding balance transitions Bucket 3 → Bucket 4.'
        ),
    )

    # ── Button Visibility Compute Fields ─────────────────────────────────────

    clm_show_customer_acceptance_btn = fields.Boolean(
        compute='_compute_clm_invoice_visibility',
        string='Show Customer Acceptance Button',
    )
    clm_show_bank_acceptance_btn = fields.Boolean(
        compute='_compute_clm_invoice_visibility',
        string='Show Bank Acceptance Button',
    )
    clm_payment_locked = fields.Boolean(
        compute='_compute_clm_invoice_visibility',
        string='Payment Locked (Bank Acceptance Required)',
    )

    @api.depends(
        'state',
        'move_type',
        'clm_customer_acceptance',
        'clm_bank_acceptance',
        'payment_state',
    )
    def _compute_clm_invoice_visibility(self):
        for move in self:
            if move.move_type != 'out_invoice' or move.state != 'posted':
                move.clm_show_customer_acceptance_btn = False
                move.clm_show_bank_acceptance_btn = False
                move.clm_payment_locked = False
                continue

            is_outstanding = move.payment_state not in ('paid', 'in_payment', 'reversed')

            # SRS §4.1: Customer acceptance — after posting, before accepted
            move.clm_show_customer_acceptance_btn = (
                not move.clm_customer_acceptance and is_outstanding
            )
            # SRS §4.2: Bank acceptance — after customer accepted, before bank
            move.clm_show_bank_acceptance_btn = (
                move.clm_customer_acceptance
                and not move.clm_bank_acceptance
                and is_outstanding
            )
            # SRS §4.3: Payment locked until bank acceptance confirmed
            move.clm_payment_locked = is_outstanding and not move.clm_bank_acceptance

    # ─────────────────────────────────────────────────────────────────────────
    # ACCEPTANCE ACTIONS  (SRS §4.1 / §4.2)
    # ─────────────────────────────────────────────────────────────────────────

    def action_clm_customer_acceptance(self):
        """
        Records customer acceptance on this invoice.
        SRS §4.1: Bucket 2 → Bucket 3 (via partner balance recompute).
        SoD: CCM or Salesperson.
        Allowed even when customer group is frozen (SRS §6.2).
        """
        if not (
            self.env.user.has_group('zencore_groups.group_zencore_clm_ccm')
            or self.env.user.has_group('zencore_groups.group_zencore_clm_salesperson')
        ):
            raise AccessError(
                "Only CCM or Salesperson can record Customer Acceptance on invoices.\n"
                "SRS §10 — Separation of Duties."
            )

        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            if move.state != 'posted':
                raise UserError(
                    f"Invoice {move.name} must be in Posted state before recording "
                    f"Customer Acceptance. Current state: {move.state}."
                )
            if move.clm_customer_acceptance:
                raise UserError(
                    f"Customer Acceptance is already recorded on invoice {move.name}."
                )

            move.write({'clm_customer_acceptance': True})
            move.message_post(
                body=Markup(
                    "<b>✔ Customer Acceptance Recorded</b><br/>"
                    "Invoice     : {inv}<br/>"
                    "Outstanding : {sym} {amt:,.2f}<br/>"
                    "Recorded by : {user}<br/>"
                    "<em>Effect: invoice exposure transitions Bucket 2 → Bucket 3</em>"
                ).format(
                    inv=move.name or '—',
                    sym=move.currency_id.symbol or '',
                    amt=move.amount_residual,
                    user=self.env.user.name,
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_clm_bank_acceptance(self):
        """
        Records bank acceptance on this invoice.
        SRS §4.2: Bucket 3 → Bucket 4 (via partner balance recompute).
        SoD: CCM or Finance.
        Allowed even when customer group is frozen (SRS §6.2).
        """
        if not (
            self.env.user.has_group('zencore_groups.group_zencore_clm_ccm')
            or self.env.user.has_group('zencore_groups.group_zencore_clm_finance')
        ):
            raise AccessError(
                "Only CCM or Finance can record Bank Acceptance on invoices.\n"
                "SRS §10 — Separation of Duties."
            )

        for move in self.filtered(lambda m: m.move_type == 'out_invoice'):
            if not move.clm_customer_acceptance:
                raise UserError(
                    f"Customer Acceptance must be recorded first on invoice {move.name}.\n"
                    "SRS §4.2: Bank Acceptance is only available after Customer Acceptance."
                )
            if move.clm_bank_acceptance:
                raise UserError(
                    f"Bank Acceptance is already recorded on invoice {move.name}."
                )

            move.write({'clm_bank_acceptance': True})
            move.message_post(
                body=Markup(
                    "<b>🏦 Bank Acceptance Recorded</b><br/>"
                    "Invoice     : {inv}<br/>"
                    "Outstanding : {sym} {amt:,.2f}<br/>"
                    "Recorded by : {user}<br/>"
                    "<em>Effect: invoice exposure transitions Bucket 3 → Bucket 4</em>"
                ).format(
                    inv=move.name or '—',
                    sym=move.currency_id.symbol or '',
                    amt=move.amount_residual,
                    user=self.env.user.name,
                ),
                subtype_xmlid='mail.mt_note',
            )

    # ─────────────────────────────────────────────────────────────────────────
    # INVOICE POST HOOK  (SRS §3.3)
    # ─────────────────────────────────────────────────────────────────────────

    def action_post(self):
        """
        SRS §3.3: Invoice posted → outstanding amount automatically enters Bucket 2
        (partner balance recompute reads invoice state via SQL in res.partner).

        SO operational stage updated: → partially_invoiced or fully_invoiced.
        Allowed even when customer is frozen (SRS §6.2).
        """
        result = super().action_post()

        for move in self.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
        ):
            sale_orders = (
                move.invoice_line_ids
                .mapped('sale_line_ids')
                .mapped('order_id')
                .filtered(lambda o: o.state not in ('cancel', 'draft'))
            )
            if sale_orders:
                sale_orders._clm_update_invoice_stage()

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # PAYMENT REGISTRATION GATE  (SRS §4.3 / §6.2)
    #
    # BUG 4 FIX: The bank acceptance pre-check was commented out, allowing
    # Finance to register payment on invoices that had not received Bank
    # Acceptance. This directly violated SRS §4.3:
    #   "Payment Registration: available only after bank acceptance."
    #
    # The check is now restored. It runs before super(), so the payment wizard
    # never opens if any selected invoice is missing bank acceptance.
    #
    # SoD: only Finance can register payments (SRS §10).
    # Freeze: payment registration is ALLOWED even when frozen (SRS §6.2).
    # ─────────────────────────────────────────────────────────────────────────

    def action_register_payment(self):
        """
        SRS §4.3: Bank acceptance required before payment registration.
        SoD: Finance only.
        Allowed even when customer group is frozen (SRS §6.2).
        """
        # SoD check
        if not self.env.user.has_group('zencore_groups.group_zencore_clm_finance'):
            raise AccessError(
                "Only Finance can register payments for customer invoices.\n"
                "SRS §10 — Separation of Duties."
            )

        # BUG 4 FIX: Bank acceptance gate — was incorrectly commented out.
        # Validate EACH invoice being paid before opening the payment wizard.
        for move in self.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
        ):
            if not move.clm_bank_acceptance:
                raise UserError(
                    "⛔  Payment Blocked — Bank Acceptance Required\n\n"
                    f"Invoice      : {move.name}\n"
                    f"Customer     : {move.partner_id.name}\n"
                    f"Outstanding  : {move.currency_id.symbol} "
                    f"{move.amount_residual:,.2f}\n\n"
                    "SRS §4.3: Payment registration is only available after "
                    "Bank Acceptance is confirmed.\n\n"
                    "Resolution:\n"
                    "  1. Confirm Customer Acceptance on the CLM Acceptance tab.\n"
                    "  2. Click '🏦 Bank Acceptance' to confirm bank processing.\n"
                    "  3. Return here to register payment."
                )

        return super().action_register_payment()


class AccountPaymentExtended(models.Model):
    """
    Payment Hook — account.payment extension.

    SRS §3.6: Payment received → reduces exposure from Bucket 4 (non-overdue)
              or Bucket 5 (overdue). Partner balance recomputes automatically
              from amount_residual on invoices — no explicit bucket move needed.

    SO operational stage: payment detected → _clm_update_payment_stage().

    ── Odoo 19: Why flush_all() + invalidate_recordset() ───────────────────────
    Odoo 19 defers reconciliation OPs and computed field recomputes until the
    next DB flush. Immediately after super().action_post():
      - account.partial.reconcile records may not yet be written
      - payment_state on account.move is still 'not_paid' in ORM cache
      - reconciled_invoice_ids is empty

    flush_all() → forces all pending writes and recomputes to DB.
    invalidate_recordset() → clears in-memory ORM cache; forces next read from DB.

    ── SoD check scope: interactive sessions only ───────────────────────────────
    Automated flows (bank statement import, SEPA batches, scheduled auto-reconcile)
    call action_post() internally as OdooBot/technical user. A hard raise blocks them.
    Guard: `not self.env.su and not ctx.get('clm_skip_sod_check')`.
    """

    _inherit = 'account.payment'

    def action_post(self):
        """
        SoD: Finance posts customer payments (interactive sessions only).
        Post-action: detect paid invoices → update SO operational stage.
        """
        if not self.env.su and not self.env.context.get('clm_skip_sod_check'):
            customer_payments = self.filtered(lambda p: p.partner_type == 'customer')
            if customer_payments:
                if not self.env.user.has_group('zencore_groups.group_zencore_clm_finance'):
                    raise AccessError(
                        "Only Finance can register and post customer payments."
                    )

        customer_payments = self.filtered(lambda p: p.partner_type == 'customer')

        result = super().action_post()

        # Force all deferred reconciliation / recompute OPs to complete.
        # Without this, reconciled_invoice_ids is empty and payment_state is stale.
        self.env.flush_all()

        for payment in customer_payments:
            # Clear stale ORM cache — must read from DB after flush_all()
            payment.invalidate_recordset(['reconciled_invoice_ids'])

            invoices = payment.reconciled_invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice'
            )
            if not invoices:
                continue

            invoices.invalidate_recordset(['payment_state', 'amount_residual'])

            sale_orders = (
                invoices.invoice_line_ids
                .mapped('sale_line_ids')
                .mapped('order_id')
                .filtered(lambda o: o.state not in ('cancel', 'draft'))
            )
            if sale_orders:
                sale_orders._clm_update_payment_stage()

        return result