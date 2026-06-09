# from odoo import models, fields, api
# from odoo.exceptions import UserError, AccessError
# from markupsafe import Markup  # BUG #1/#2 FIX: required for safe HTML in message_post

# # Fields that must NEVER be written directly by users.
# # Stage machine controls these exclusively.
# _CLM_PROTECTED_FIELDS = frozenset({
#     'clm_state',
#     'clm_customer_acceptance',
#     'clm_bank_acceptance',
# })


# class SaleOrderExtended(models.Model):
#     """
#     CLM Stage Machine — sale.order extension.

#     Stage flow (automatic, driven by business events only):
#       pi → bucket1      : delivery validated         (stock_picking_extended)
#       bucket1 → bucket2 : invoice posted             (account_move_extended)
#       bucket2 → bucket3 : customer acceptance button (action_clm_customer_acceptance)
#       bucket3 → bucket4 : bank acceptance button     (action_clm_bank_acceptance)
#       bucket4 → paid    : full payment received      (account_move_extended)

#     Freeze enforcement (SRS §6.2):
#       BLOCKED: create, action_confirm, delivery validation
#       ALLOWED: invoice posting, customer acceptance, bank acceptance, payment

#     SoD enforcement (SRS §10):
#       create         → Salesperson OR Sales Manager
#       action_confirm → Sales Manager only
#       delivery       → Warehouse only (in stock_picking_extended)
#       invoice create → TDO only (in _create_invoices)
#       invoice post   → TDO only (in account_move_extended)
#       payment        → Finance only (in account_move_extended)
#     """

#     _inherit = 'sale.order'

#     # ─────────────────────────────────────────────────────────────────────────
#     # CLM STAGE FIELD
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_state = fields.Selection(
#         selection=[
#             ('pi',                  'Proforma Invoice'),
#             ('partially_delivered', 'Partially Delivered'),
#             ('fully_delivered',     'Fully Delivered'),
#             ('partially_invoiced',  'Partially Invoiced'),
#             ('fully_invoiced',      'Fully Invoiced'),
#             ('partially_paid',      'Partially Paid'),
#             ('fully_paid',          'Fully Paid'),
#         ],
#         string='CLM Stage',
#         default='pi',
#         readonly=True,
#         tracking=True,
#         copy=False,
#         index=True,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # ACCEPTANCE CONTROL FIELDS
#     # readonly=True on field definition; only internal methods write these.
#     # write() override below provides a second enforcement layer against RPC.
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_customer_acceptance = fields.Boolean(
#         string='Customer Acceptance',
#         readonly=True,
#         tracking=True,
#         copy=False,
#         help='Set when customer has accepted documents. Triggers move to Bucket 3.',
#     )
#     clm_bank_acceptance = fields.Boolean(
#         string='Bank Acceptance',
#         readonly=True,
#         tracking=True,
#         copy=False,
#         help='Set when bank has accepted documents. Triggers move to Bucket 4.',
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # VISIBILITY FLAGS — Drive show/hide in views
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_show_customer_acceptance_btn = fields.Boolean(
#         compute='_compute_clm_visibility',
#         string='Show Customer Acceptance Button',
#     )
#     clm_show_bank_acceptance_btn = fields.Boolean(
#         compute='_compute_clm_visibility',
#         string='Show Bank Acceptance Button',
#     )
#     clm_show_payment_action = fields.Boolean(
#         compute='_compute_clm_visibility',
#         string='Payment Available',
#     )

#     @api.depends('clm_state', 'clm_customer_acceptance', 'clm_bank_acceptance')
#     def _compute_clm_visibility(self):
#         for order in self:
#             order.clm_show_customer_acceptance_btn = (
#                 order.clm_state == 'bucket2' and not order.clm_customer_acceptance
#             )
#             order.clm_show_bank_acceptance_btn = (
#                 order.clm_state == 'bucket3' and not order.clm_bank_acceptance
#             )
#             order.clm_show_payment_action = (
#                 order.clm_bank_acceptance and order.clm_state == 'bucket4'
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # WRITE PROTECTION — Prevent RPC bypass of stage machine
#     # ─────────────────────────────────────────────────────────────────────────

#     def write(self, vals):
#         """
#         Block direct writes to CLM stage/acceptance fields from external callers.
#         Internal methods use with_context(clm_internal_write=True).
#         This prevents JSON-RPC bypass of the stage machine.
#         """
#         protected = _CLM_PROTECTED_FIELDS & set(vals.keys())
#         if protected and not self.env.context.get('clm_internal_write'):
#             raise AccessError(
#                 "CLM stage fields cannot be modified directly.\n"
#                 "Stage transitions are controlled by business events only.\n"
#                 "Fields blocked: %s" % ', '.join(sorted(protected))
#             )
#         return super().write(vals)

#     # ─────────────────────────────────────────────────────────────────────────
#     # FREEZE CHECK — Core group-level enforcement
#     # ─────────────────────────────────────────────────────────────────────────

#     # def _clm_check_group_freeze(self, operation_label):
#     #     """
#     #     Validates the entire customer group for freeze before any blocked operation.
#     #     SRS §7 — group-wide enforcement: if ANY child is frozen, ALL are blocked.

#     #     Group resolution:
#     #       child partner → group_head = partner.parent_id
#     #       standalone    → group_head = partner itself
#     #       All children of group_head are checked.

#     #     Raises UserError with full breach details (SRS §6.4 / §7.10).
#     #     """
#     #     partner = self.partner_id
#     #     if not partner:
#     #         return

#     #     group_head = partner.parent_id if partner.parent_id else partner
#     #     all_members = group_head | group_head.child_ids.filtered(lambda c: c.active)

#     #     frozen_members = all_members.filtered(lambda p: p.clm_is_frozen)
#     #     if not frozen_members:
#     #         return

#     #     breached = frozen_members[0]
#     #     breach = breached.clm_get_first_breach()

#     #     currency = breached.currency_id
#     #     fmt = lambda amt: f"{currency.symbol} {amt:,.2f}"

#     #     if not breach:
#     #         raise UserError(
#     #             f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
#     #             f"Group           : {group_head.name}\n"
#     #             f"Frozen Customer : {breached.name}\n\n"
#     #             f"Contact the Credit & Collections Manager to resolve."
#     #         )

#     #     raise UserError(
#     #         f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
#     #         f"Group           : {group_head.name}\n"
#     #         f"Frozen Customer : {breached.name}\n"
#     #         f"Bucket          : {breach['bucket']}\n"
#     #         f"Defined Limit   : {fmt(breach['limit'])}\n"
#     #         f"Current Exposure: {fmt(breach['exposure'])}\n"
#     #         f"Excess Amount   : {fmt(breach['excess'])}\n\n"
#     #         f"Resolution: reduce exposure or submit a Limit Increase Request (CCM → FM)."
#     #     )

#     def _clm_check_group_freeze(self, operation_label):
#         """
#         SRS §3.3 / §3.4 — Blocks the operation if the customer's credit group is frozen.

#         Uses partner.bucket_freeze_active as the single source of truth.
#         bucket_freeze_active already encodes the full group resolution logic,
#         so this method only needs to read it and format the error message.

#         Freeze blocks (SRS §3.3):
#         - New PI issuance     (sale.order.create)
#         - SO confirmation     (action_confirm)
#         - Delivery validation (stock_picking.button_validate)

#         Freeze NEVER blocks (SRS §3.3):
#         - Invoice posting, customer/bank acceptance, payment registration.
#         """
#         partner = self.partner_id
#         if not partner:
#             return

#         # Single field read — group resolution is inside bucket_freeze_active
#         if not partner.bucket_freeze_active:
#             return

#         # ── Find the member that caused the freeze (for error details) ────────
#         # We need to identify WHICH partner is breached and WHICH bucket.
#         group_head = partner.parent_id if partner.parent_id else partner
#         all_members = group_head | group_head.child_ids.filtered(lambda c: c.active)

#         # Find the first member with a personal breach
#         breached = next(
#             (m for m in all_members if m.clm_is_frozen),
#             None,
#         )

#         if not breached:
#             # bucket_freeze_active = True but no member found — cache race condition.
#             # Raise a generic message rather than silently allowing the operation.
#             raise UserError(
#                 f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
#                 f"Group           : {group_head.name}\n"
#                 f"Customer        : {partner.name}\n\n"
#                 "A credit limit has been exceeded. Contact the Credit & Collections Manager."
#             )

#         breach = breached.clm_get_first_breach()
#         currency = breached.currency_id
#         fmt = lambda amt: f"{currency.symbol or ''} {amt:,.2f}".strip()

#         # ── Partner context in message ────────────────────────────────────────
#         # If the frozen member is different from the order's partner, name both.
#         if breached.id != partner.id:
#             who = (
#                 f"Group           : {group_head.name}\n"
#                 f"Order Customer  : {partner.name}\n"
#                 f"Frozen Member   : {breached.name} (sibling in group)\n"
#             )
#         else:
#             who = (
#                 f"Group           : {group_head.name}\n"
#                 f"Customer        : {partner.name}\n"
#             )

#         if not breach:
#             raise UserError(
#                 f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
#                 + who +
#                 "\nContact the Credit & Collections Manager to resolve the freeze."
#             )

#         raise UserError(
#             f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
#             + who +
#             f"Bucket          : {breach['bucket']}\n"
#             f"Defined Limit   : {fmt(breach['limit'])}\n"
#             f"Current Exposure: {fmt(breach['exposure'])}\n"
#             f"Excess Amount   : {fmt(breach['excess'])}\n\n"
#             "Resolution: reduce exposure in the breached bucket, or submit a\n"
#             "Limit Increase Request via CCM → FM approval workflow."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # BLOCKED OPERATION OVERRIDES (SRS §6.2)
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.model_create_multi
#     def create(self, vals_list):
#         """
#         SoD: Only Salesperson or Sales Manager can create quotations.
#         Freeze: Block creation if customer group is frozen (SRS §6.2).
#         """
#         if not (
#             self.env.user.has_group('zencore_groups.group_zencore_clm_salesperson')
#             or self.env.user.has_group('zencore_groups.group_zencore_clm_sales_manager')
#         ):
#             raise AccessError(
#                 "Only Salesperson or Sales Manager can create quotations."
#             )

#         for vals in vals_list:
#             vals['clm_state'] = 'pi'

#         orders = super().create(vals_list)
#         for order in orders:
#             if order.partner_id:
#                 order._clm_check_group_freeze('Proforma Invoice Creation')
#         return orders

#     def action_confirm(self):
#         """
#         SoD: Only Sales Manager can confirm a Sales Order.
#         Freeze: Block confirmation if customer group is frozen (SRS §6.2).
#         """
#         if not self.env.user.has_group('zencore_groups.group_zencore_clm_sales_manager'):
#             raise AccessError("Only Sales Manager can confirm a Sales Order.")
#         for order in self:
#             order._clm_check_group_freeze('Sales Order Confirmation')
#         return super().action_confirm()

#     def _create_invoices(self, grouped=False, final=False, date=None):
#         """
#         SoD: Only TDO can create invoices (SRS §10).
#         No freeze check — invoice creation is ALLOWED even when frozen (SRS §6.2).
#         """
#         if not self.env.user.has_group('zencore_groups.group_zencore_clm_tdo'):
#             raise AccessError(
#                 "Only TDO (Territory/Technical Delivery Officer) can create invoices."
#             )
#         return super()._create_invoices(grouped=grouped, final=final, date=date)

#     # ─────────────────────────────────────────────────────────────────────────
#     # ACCEPTANCE ACTIONS — Called by buttons, not by users directly
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_clm_customer_acceptance(self):
#         """
#         Records customer acceptance → moves stage: Bucket 2 → Bucket 3.
#         SRS §4.1: Allowed even when frozen (SRS §6.2).
#         SoD: CCM or Salesperson may record.
#         """
#         if not (
#             self.env.user.has_group('zencore_groups.group_zencore_clm_ccm')
#             or self.env.user.has_group('zencore_groups.group_zencore_clm_salesperson')
#         ):
#             raise AccessError(
#                 "Only CCM or Salesperson can record Customer Acceptance."
#             )
#         for order in self:
#             if order.clm_state != 'bucket2':
#                 stage_label = dict(order._fields['clm_state'].selection).get(order.clm_state)
#                 raise UserError(
#                     f"Customer Acceptance requires order to be in Bucket 2.\n"
#                     f"Current stage: {stage_label}"
#                 )
#             order.with_context(clm_internal_write=True).write({
#                 'clm_customer_acceptance': True,
#                 'clm_state': 'bucket3',
#             })
#             order._clm_log_stage_change(
#                 from_stage='Bucket 2',
#                 to_stage='Bucket 3',
#                 trigger='Customer Acceptance Recorded',
#             )

#     def action_clm_bank_acceptance(self):
#         """
#         Records bank acceptance → moves stage: Bucket 3 → Bucket 4.
#         SRS §4.2: Allowed even when frozen (SRS §6.2).
#         SoD: CCM or Finance may record.
#         """
#         if not (
#             self.env.user.has_group('zencore_groups.group_zencore_clm_ccm')
#             or self.env.user.has_group('zencore_groups.group_zencore_clm_finance')
#         ):
#             raise AccessError(
#                 "Only CCM or Finance can record Bank Acceptance."
#             )
#         for order in self:
#             if order.clm_state != 'bucket3':
#                 stage_label = dict(order._fields['clm_state'].selection).get(order.clm_state)
#                 raise UserError(
#                     f"Bank Acceptance requires order to be in Bucket 3.\n"
#                     f"Current stage: {stage_label}"
#                 )
#             order.with_context(clm_internal_write=True).write({
#                 'clm_bank_acceptance': True,
#                 'clm_state': 'bucket4',
#             })
#             order._clm_log_stage_change(
#                 from_stage='Bucket 3',
#                 to_stage='Bucket 4',
#                 trigger='Bank Acceptance Recorded',
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # INTERNAL STAGE SETTERS — Called by event hooks only
#     # All use clm_internal_write=True to bypass the write() guard.
#     # ─────────────────────────────────────────────────────────────────────────
#     # def _clm_get_delivery_progress(self):
#     #     self.ensure_one()

#     #     move_lines = self.env['stock.move.line'].search([
#     #         ('move_id.sale_line_id.order_id', '=', self.id),
#     #         ('state', '=', 'done'),
#     #     ])

#     #     delivered_qty = sum(move_lines.mapped('qty_done'))

#     #     ordered_qty = sum(self.order_line.mapped('product_uom_qty'))

#     #     return delivered_qty, ordered_qty

#      # ─────────────────────────────────────────────────────────────────────────
#     # DELIVERY PROGRESS HELPER
#     # ─────────────────────────────────────────────────────────────────────────
 
#     def _clm_get_delivery_progress(self):
#         """
#         Returns (delivered_qty, ordered_qty) for this order.
 
#         Reads from stock.move (not stock.move.line) using quantity_done,
#         which is the correct Odoo 17+ API.  stock.move.line.qty_done was
#         removed from Community in Odoo 17 — it only exists in the Enterprise
#         stock_barcode module — so any direct use of that field raises a
#         KeyError on Community installations.
 
#         Filters:
#           - sale_line_id.order_id = this order   (sale-linked moves only)
#           - picking_type_code = 'outgoing'        (customer delivery only;
#                                                    excludes receipts / returns)
#           - state = 'done'                        (validated moves only)
 
#         Both quantities are raw floats in each line's product UoM.  Cross-UoM
#         normalisation is intentionally deferred to the caller; for the partial
#         vs full decision in stock_picking_extended the comparison is always
#         within the same order so UoM consistency holds.
#         """
#         self.ensure_one()
#         done_moves = self.env['stock.move'].search([
#             ('sale_line_id.order_id', '=', self.id),
#             ('picking_type_id.code', '=', 'outgoing'),
#             ('state', '=', 'done'),
#         ])
#         delivered_qty = sum(done_moves.mapped('quantity_done'))
#         ordered_qty = sum(self.order_line.mapped('product_uom_qty'))
#         return delivered_qty, ordered_qty

#     def _clm_move_to_partially_delivered(self):
#         """
#         PI → Partially Delivered.
#         Triggered by: first partial delivery validated.
#         Guard: order must still be in the 'pi' stage.
#         """
#         orders = self.filtered(lambda o: o.clm_state == 'pi')
#         if orders:
#             orders.with_context(clm_internal_write=True).write(
#                 {'clm_state': 'partially_delivered'}
#             )
#             for order in orders:
#                 order._clm_log_stage_change(
#                     from_stage='Proforma Invoice',
#                     to_stage='Partially Delivered',
#                     trigger='First Partial Delivery Validated',
#                 )
 
#     def _clm_move_to_fully_delivered(self):
#         """
#         PI → Fully Delivered  OR  Partially Delivered → Fully Delivered.
#         Triggered by: final (or only) delivery validated.
 
#         BUG FIX: original filtered on clm_state == 'pi' only, which meant
#         a final delivery on an already-partially-delivered order was silently
#         dropped.  Correct guard is either 'pi' (single complete delivery)
#         or 'partially_delivered' (final delivery after partial).
#         """
#         orders = self.filtered(
#             lambda o: o.clm_state in ('pi', 'partially_delivered')
#         )
#         if orders:
#             orders.with_context(clm_internal_write=True).write(
#                 {'clm_state': 'fully_delivered'}
#             )
#             for order in orders:
#                 order._clm_log_stage_change(
#                     from_stage=dict(
#                         order._fields['clm_state'].selection
#                     ).get(order.clm_state, order.clm_state),
#                     to_stage='Fully Delivered',
#                     trigger='Final Delivery Validated',
#                 )

#     def _clm_move_to_partially_invoiced(self):
#         """First invoice → Partially Delivered → Partially Invoiced."""
#         orders = self.filtered(lambda o: o.clm_state == 'partially_delivered')
#         if orders:
#             orders.with_context(clm_internal_write=True).write({'clm_state': 'partially_invoiced'})
#             for order in orders:
#                 order._clm_log_stage_change(
#                     from_stage='Partially Delivered',
#                     to_stage='Partially Invoiced',
#                     trigger='First Invoice Posted',
#                 )

#     def _clm_move_to_fully_invoiced(self):
#         """Final invoice → Partially Invoiced → Fully Invoiced."""
#         orders = self.filtered(lambda o: o.clm_state == 'partially_invoiced')
#         if orders:
#             orders.with_context(clm_internal_write=True).write({'clm_state': 'fully_invoiced'})
#             for order in orders:
#                 order._clm_log_stage_change(
#                     from_stage='Partially Invoiced',
#                     to_stage='Fully Invoiced',
#                     trigger='Final Invoice Posted',
#                 )
#     def _clm_move_to_partially_paid(self):
#         """First payment → Partially Invoiced → Partially Paid."""
#         orders = self.filtered(lambda o: o.clm_state == 'partially_invoiced')
#         if orders:
#             orders.with_context(clm_internal_write=True).write({'clm_state': 'partially_paid'})
#             for order in orders:
#                 order._clm_log_stage_change(
#                     from_stage='Partially Invoiced',
#                     to_stage='Partially Paid',
#                     trigger='First Payment Received',
#                 )
#     def _clm_move_to_fully_paid(self):
#         """Final payment → Partially Paid → Fully Paid."""
#         orders = self.filtered(lambda o: o.clm_state == 'partially_paid')
#         if orders:
#             orders.with_context(clm_internal_write=True).write({'clm_state': 'fully_paid'})
#             for order in orders:
#                 order._clm_log_stage_change(
#                     from_stage='Partially Paid',
#                     to_stage='Fully Paid',
#                     trigger='Final Payment Received',
#                 )

#     # def _clm_move_to_bucket1(self):
#     #     """Delivery validated → PI → Bucket 1 (SRS §3.2)."""
#     #     orders = self.filtered(lambda o: o.clm_state == 'pi')
#     #     if orders:
#     #         orders.with_context(clm_internal_write=True).write({'clm_state': 'bucket1'})
#     #         for order in orders:
#     #             order._clm_log_stage_change(
#     #                 from_stage='Proforma Invoice',
#     #                 to_stage='Bucket 1',
#     #                 trigger='Delivery Validated',
#     #             )

#     # def _clm_move_to_bucket2(self):
#     #     """Invoice posted → Bucket 1 → Bucket 2 (SRS §3.3)."""
#     #     orders = self.filtered(lambda o: o.clm_state == 'bucket1')
#     #     if orders:
#     #         orders.with_context(clm_internal_write=True).write({'clm_state': 'bucket2'})
#     #         for order in orders:
#     #             order._clm_log_stage_change(
#     #                 from_stage='Bucket 1',
#     #                 to_stage='Bucket 2',
#     #                 trigger='Invoice Posted',
#     #             )

#     def _clm_move_to_paid(self):
#         """
#         Full payment received → Bucket 4 → Paid (SRS §3.6).

#         BUG #7 FIX: Added diagnostic chatter note when payment is detected but
#         the order is NOT in bucket4 or bank acceptance is missing. Without this,
#         Finance had no visibility into why the stage didn't change after payment.

#         Filter logic:
#           - clm_state == 'bucket4'    : order must be in the correct pre-paid stage
#           - clm_bank_acceptance       : guaranteed True for any bucket4 order
#                                         (set atomically when entering bucket4), but
#                                         kept as an explicit safety guard.
#         """
#         orders_to_pay = self.filtered(
#             lambda o: o.clm_state == 'bucket4' and o.clm_bank_acceptance
#         )

#         if not orders_to_pay:
#             # ── Diagnostic: log on orders that SHOULD have moved but didn't ──
#             # Only log on active orders (not already paid, not cancelled)
#             skipped = self.filtered(
#                 lambda o: o.clm_state not in ('paid', 'pi') and o.state != 'cancel'
#             )
#             for order in skipped:
#                 stage_label = dict(
#                     order._fields['clm_state'].selection
#                 ).get(order.clm_state, order.clm_state)
#                 order.message_post(
#                     body=Markup(
#                         "<b>⚠ Payment detected — CLM stage not updated</b><br/>"
#                         "Order is in stage <b>{stage}</b>, "
#                         "expected <b>Bucket 4</b> with bank acceptance confirmed.<br/>"
#                         "If payment is complete, verify bank acceptance is recorded "
#                         "on the Credit Control tab."
#                     ).format(stage=stage_label),
#                     subtype_xmlid='mail.mt_note',
#                 )
#             return

#         orders_to_pay.with_context(clm_internal_write=True).write({'clm_state': 'paid'})
#         for order in orders_to_pay:
#             order._clm_log_stage_change(
#                 from_stage='Bucket 4',
#                 to_stage='Paid',
#                 trigger='Full Payment Received',
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # AUDIT LOGGING — Chatter note on every stage transition
#     # ─────────────────────────────────────────────────────────────────────────

#     def _clm_log_stage_change(self, from_stage, to_stage, trigger):
#         """
#         Posts a structured chatter note on every CLM stage transition.
#         Uses mt_note subtype — internal audit only, no email to followers.

#         BUG #1 FIX:
#           - Original used plain f-string concatenation with no <br/> tags
#             → all text appeared on one garbled line in the chatter.
#           - Original lacked Markup() wrapper → HTML tags were escaped to
#             visible &lt;b&gt; text in Odoo 17+.
#           - Fixed: Markup("...{var}...").format(...) auto-escapes every
#             variable while keeping the surrounding HTML trusted.
#         """
#         self.ensure_one()
#         self.message_post(
#             body=Markup(
#                 "<b>Stage Transition</b><br/>"
#                 "From   : {from_stage}<br/>"
#                 "To     : {to_stage}<br/>"
#                 "Trigger: {trigger}<br/>"
#                 "By     : {user}"
#             ).format(
#                 from_stage=from_stage,
#                 to_stage=to_stage,
#                 trigger=trigger,
#                 user=self.env.user.name,
#             ),
#             subtype_xmlid='mail.mt_note',
#         )

from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError
from markupsafe import Markup

# Only clm_state is protected now.
# clm_customer_acceptance / clm_bank_acceptance moved to account.move (SRS §4).
_CLM_PROTECTED_FIELDS = frozenset({'clm_state'})

# Forward-only stage ordering. _clm_set_stage() uses this to prevent regressions.
_CLM_STAGE_ORDER = {
    'pi':                  0,
    'partially_delivered': 1,
    'fully_delivered':     2,
    'partially_invoiced':  3,
    'fully_invoiced':      4,
    'partially_paid':      5,
    'fully_paid':          6,
}


class SaleOrderExtended(models.Model):
    """
    CLM Operational Stage Machine — sale.order extension.

    ── What this model tracks ────────────────────────────────────────────────
    clm_state: OPERATIONAL stage — "what happened to this SO?"
      pi → partially_delivered → fully_delivered
         → partially_invoiced  → fully_invoiced
         → partially_paid      → fully_paid

    This is independent from credit exposure buckets (SRS §2.1 / §10):
    "Sales Stages are independent from Credit Exposure Buckets."

    ── What this model does NOT track ───────────────────────────────────────
    Customer Acceptance, Bank Acceptance → these live on account.move (SRS §4).
    Bucket exposure → computed on res.partner from invoice states (SRS §3.1).

    ── Stage Transition Triggers ─────────────────────────────────────────────
      PI            → delivery stage   : stock_picking_extended._action_done()
      delivery stage → invoice stage   : account_move_extended.action_post()
      invoice stage  → payment stage   : account_payment_extended.action_post()

    ── Freeze Enforcement (SRS §6.2) ─────────────────────────────────────────
      BLOCKED: create (PI issuance), action_confirm, delivery validation
      ALLOWED: invoice posting, acceptance, payment, collection

    ── SoD (SRS §10) ─────────────────────────────────────────────────────────
      create          : Salesperson OR Sales Manager
      action_confirm  : Sales Manager only
      delivery        : Warehouse only (stock_picking_extended)
      invoice create  : TDO only (_create_invoices)
      invoice post    : TDO only (account_move_extended)
      payment         : Finance only (account_payment_extended)
    """

    _inherit = 'sale.order'

    # ─────────────────────────────────────────────────────────────────────────
    # CLM OPERATIONAL STAGE FIELD  (SRS §2.2)
    # ─────────────────────────────────────────────────────────────────────────

    clm_state = fields.Selection(
        selection=[
            ('pi',                  'Proforma Invoice'),
            ('partially_delivered', 'Partially Delivered'),
            ('fully_delivered',     'Fully Delivered'),
            ('partially_invoiced',  'Partially Invoiced'),
            ('fully_invoiced',      'Fully Invoiced'),
            ('partially_paid',      'Partially Paid'),
            ('fully_paid',          'Fully Paid'),
        ],
        string='CLM Stage',
        default='pi',
        readonly=True,
        tracking=True,
        copy=False,
        index=True,
        help=(
            'SRS §2.2 — Operational stage. System-controlled. '
            'Users cannot manually change this. '
            'Independent from credit exposure buckets (SRS §10).'
        ),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # VISIBILITY / SUMMARY FIELDS
    # Reflect the acceptance status of LINKED INVOICES — read-only on SO.
    # The actual acceptance buttons live on account.move (SRS §4).
    # ─────────────────────────────────────────────────────────────────────────

    clm_show_customer_acceptance_btn = fields.Boolean(
        compute='_compute_clm_visibility',
        string='Invoices Pending Customer Acceptance',
        help='True if any linked posted invoice is awaiting Customer Acceptance.',
    )
    clm_show_bank_acceptance_btn = fields.Boolean(
        compute='_compute_clm_visibility',
        string='Invoices Pending Bank Acceptance',
        help='True if any linked invoice has Customer Acceptance but awaits Bank Acceptance.',
    )
    clm_show_payment_action = fields.Boolean(
        compute='_compute_clm_visibility',
        string='Invoices Ready for Payment',
        help='True if any linked invoice has Bank Acceptance confirmed.',
    )

    # @api.depends('clm_state', 'invoice_ids', 'invoice_ids.state',
    #              'invoice_ids.move_type', 'invoice_ids.payment_state')
    # def _compute_clm_visibility(self):
    #     for order in self:
    #         posted_inv = order.invoice_ids.filtered(
    #             lambda i: (
    #                 i.move_type == 'out_invoice'
    #                 and i.state == 'posted'
    #                 and i.payment_state not in ('paid', 'in_payment', 'reversed')
    #             )
    #         )
    #         order.clm_show_customer_acceptance_btn = (
    #             not inv.clm_customer_acceptance for inv in posted_inv
    #         )
    #         order.clm_show_bank_acceptance_btn = any(
    #             inv.clm_customer_acceptance and not inv.clm_bank_acceptance
    #             for inv in posted_inv
    #         )
    #         order.clm_show_payment_action = any(
    #             inv.clm_bank_acceptance for inv in posted_inv
    #         )

    @api.depends(
        'clm_state',
        'invoice_ids',
        'invoice_ids.state',
        'invoice_ids.move_type',
        'invoice_ids.payment_state',
        'invoice_ids.clm_customer_acceptance',
        'invoice_ids.clm_bank_acceptance',
    )
    def _compute_clm_visibility(self):
        for order in self:

            posted_inv = order.invoice_ids.filtered(
                lambda i: (
                    i.move_type == 'out_invoice'
                    and i.state == 'posted'
                    and i.payment_state not in ('paid', 'in_payment', 'reversed')
                )
            )

            # -------------------------
            # Customer Acceptance Button
            # -------------------------
            order.clm_show_customer_acceptance_btn = any(
                not inv.clm_customer_acceptance
                for inv in posted_inv
            )

            # -------------------------
            # Bank Acceptance Button
            # -------------------------
            order.clm_show_bank_acceptance_btn = any(
                inv.clm_customer_acceptance and not inv.clm_bank_acceptance
                for inv in posted_inv
            )

            # -------------------------
            # Payment Action
            # -------------------------
            order.clm_show_payment_action = any(
                inv.clm_bank_acceptance
                for inv in posted_inv
            )

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION — Prevent RPC / JSON-RPC bypass of stage machine
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        protected = _CLM_PROTECTED_FIELDS & set(vals.keys())
        if protected and not self.env.context.get('clm_internal_write'):
            raise AccessError(
                "CLM stage fields cannot be modified directly.\n"
                "Stage transitions are controlled exclusively by business events.\n"
                "Fields blocked: %s" % ', '.join(sorted(protected))
            )
        return super().write(vals)

    # ─────────────────────────────────────────────────────────────────────────
    # FREEZE CHECK — Group-level enforcement (SRS §6.1 / §7)
    # ─────────────────────────────────────────────────────────────────────────

    def _clm_check_group_freeze(self, operation_label):
        """
        SRS §6 / §7 — Group-wide credit freeze.
        Uses partner.bucket_freeze_active (canonical freeze field).
        Raises UserError with full breach details (SRS §6.4).

        Freeze BLOCKS: PI creation, SO confirmation, delivery validation.
        Freeze NEVER blocks: invoicing, acceptance, payment, collection.
        """
        partner = self.partner_id
        if not partner:
            return

        if not partner.bucket_freeze_active:
            return

        # Identify the member that triggered the freeze
        group_head = partner.parent_id if partner.parent_id else partner
        all_members = group_head | group_head.child_ids.filtered(lambda c: c.active)
        breached = next((m for m in all_members if m.clm_is_frozen), None)

        if not breached:
            raise UserError(
                f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
                f"Group    : {group_head.name}\n"
                f"Customer : {partner.name}\n\n"
                "A credit limit has been exceeded. Contact the CCM to resolve."
            )

        breach = breached.clm_get_first_breach()
        sym = breached.currency_id.symbol or ''
        fmt = lambda amt: f"{sym} {amt:,.2f}".strip()

        who = (
            f"Group           : {group_head.name}\n"
            f"Order Customer  : {partner.name}\n"
            f"Frozen Member   : {breached.name} (group sibling)\n"
            if breached.id != partner.id
            else
            f"Group           : {group_head.name}\n"
            f"Customer        : {partner.name}\n"
        )

        if not breach:
            raise UserError(
                f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
                + who
                + "\nContact the CCM to resolve the freeze."
            )

        raise UserError(
            f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
            + who
            + f"Bucket          : {breach['bucket']}\n"
            + f"Defined Limit   : {fmt(breach['limit'])}\n"
            + f"Current Exposure: {fmt(breach['exposure'])}\n"
            + f"Excess Amount   : {fmt(breach['excess'])}\n\n"
            "Resolution: reduce exposure in the breached bucket, or submit a\n"
            "Limit Increase Request via CCM → FM approval workflow."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCKED OPERATION OVERRIDES  (SRS §6.2)
    # ─────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """
        SoD: Salesperson or Sales Manager creates quotations.
        Freeze: Block PI creation if group is frozen (SRS §6.2).
        """
        if not (
            self.env.user.has_group('zencore_groups.group_zencore_clm_salesperson')
            or self.env.user.has_group('zencore_groups.group_zencore_clm_sales_manager')
        ):
            raise AccessError(
                "Only Salesperson or Sales Manager can create quotations/orders."
            )

        for vals in vals_list:
            vals.setdefault('clm_state', 'pi')

        orders = super().create(vals_list)

        for order in orders:
            if order.partner_id:
                order._clm_check_group_freeze('Proforma Invoice Creation')

        return orders

    def action_confirm(self):
        """
        SoD: Sales Manager only.
        Freeze: Block confirmation if group is frozen (SRS §6.2).
        """
        if not self.env.user.has_group('zencore_groups.group_zencore_clm_sales_manager'):
            raise AccessError("Only Sales Manager can confirm a Sales Order.")
        for order in self:
            order._clm_check_group_freeze('Sales Order Confirmation')
        return super().action_confirm()

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        SoD: TDO only (SRS §10).
        No freeze check — invoice creation is ALLOWED when frozen (SRS §6.2).
        """
        if not self.env.user.has_group('zencore_groups.group_zencore_clm_tdo'):
            raise AccessError(
                "Only TDO (Territory/Technical Delivery Officer) can create invoices."
            )
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL STAGE MACHINE — called by event hooks ONLY
    # ─────────────────────────────────────────────────────────────────────────

    def _clm_set_stage(self, new_stage, trigger='System event'):
        """
        Core stage setter. Moves forward only (prevents regressions).
        Logs a chatter note on every actual transition.

        Algorithm:
          1. Look up current and target rank in _CLM_STAGE_ORDER.
          2. Only write if target rank > current rank.
          3. Post chatter note with from/to/trigger.
        """
        for order in self:
            current_rank = _CLM_STAGE_ORDER.get(order.clm_state, -1)
            target_rank = _CLM_STAGE_ORDER.get(new_stage, -1)

            if target_rank <= current_rank:
                # Already at or past target — skip silently
                continue

            from_label = dict(
                order._fields['clm_state'].selection
            ).get(order.clm_state, order.clm_state)
            to_label = dict(
                order._fields['clm_state'].selection
            ).get(new_stage, new_stage)

            order.with_context(clm_internal_write=True).write({'clm_state': new_stage})
            order._clm_log_stage_change(
                from_stage=from_label,
                to_stage=to_label,
                trigger=trigger,
            )

    # ── Delivery Stage Setters (called by stock_picking_extended) ─────────────

    def _clm_move_to_partially_delivered(self):
        """First/partial delivery → moves toward partially_delivered."""
        self._clm_set_stage('partially_delivered', trigger='Partial Delivery Validated')

    def _clm_move_to_fully_delivered(self):
        """Full delivery → moves toward fully_delivered."""
        self._clm_set_stage('fully_delivered', trigger='Full Delivery Validated')

    # ── Invoice Stage Updater (called by account_move_extended.action_post) ───

    def _clm_update_invoice_stage(self):
        """
        Called when any invoice linked to this SO is posted.
        Determines whether the SO should move to partially_invoiced or fully_invoiced
        based on Odoo's computed invoice_status field.
        """
        for order in self:
            posted_invoices = order.invoice_ids.filtered(
                lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
            )
            if not posted_invoices:
                continue

            # Odoo's invoice_status:
            #   'invoiced'   → all delivered quantities have been invoiced
            #   'to invoice' → some delivered quantities remain to invoice
            #   'nothing'    → nothing to invoice (typically before delivery)
            if order.invoice_status == 'invoiced':
                order._clm_set_stage('fully_invoiced', trigger='All Deliveries Fully Invoiced')
            else:
                order._clm_set_stage('partially_invoiced', trigger='Invoice Posted (Partial)')

    # ── Payment Stage Updater (called by AccountPaymentExtended.action_post) ──

    def _clm_update_payment_stage(self):
        """
        Called after a payment is posted and reconciled.
        Checks ALL posted customer invoices for this SO to determine
        whether to move to partially_paid or fully_paid.
        """
        for order in self:
            invoices = order.invoice_ids.filtered(
                lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
            )
            if not invoices:
                continue

            # Invalidate stale cache — payment_state recomputed after flush_all()
            invoices.invalidate_recordset(['payment_state', 'amount_residual'])

            all_paid = all(
                inv.payment_state in ('paid', 'in_payment') for inv in invoices
            )
            any_paid = any(
                inv.payment_state in ('paid', 'in_payment') for inv in invoices
            )

            if all_paid:
                order._clm_set_stage('fully_paid', trigger='All Invoices Fully Paid')
            elif any_paid:
                order._clm_set_stage('partially_paid', trigger='Invoice Partially Paid')

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT LOGGING — Chatter note on every CLM stage transition
    # ─────────────────────────────────────────────────────────────────────────

    def _clm_log_stage_change(self, from_stage, to_stage, trigger):
        """
        Posts a structured internal chatter note on every CLM stage transition.
        mt_note = internal only; no email to followers.
        Uses Markup() to prevent XSS while keeping HTML safe.
        """
        self.ensure_one()
        self.message_post(
            body=Markup(
                "<b>CLM Stage Transition</b><br/>"
                "From    : {from_stage}<br/>"
                "To      : {to_stage}<br/>"
                "Trigger : {trigger}<br/>"
                "By      : {user}"
            ).format(
                from_stage=from_stage,
                to_stage=to_stage,
                trigger=trigger,
                user=self.env.user.name,
            ),
            subtype_xmlid='mail.mt_note',
        )