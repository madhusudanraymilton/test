# from odoo import models, fields, api
# from odoo.exceptions import UserError


# class SaleOrderExtended(models.Model):
#     """
#     Stage Machine — sale.order extension.

#     Stage flow (automatic, driven by business events):
#       pi → bucket1 (delivery validated)
#       bucket1 → bucket2 (invoice posted)
#       bucket2 → bucket3 (customer acceptance)
#       bucket3 → bucket4 (bank acceptance)
#       bucket4 → paid (full payment received)

#     Users CANNOT manually change clm_state (readonly=True on field).
#     Freeze check runs on: create, action_confirm, delivery validation.
#     Acceptance buttons trigger stage moves on: bucket2 and bucket3.
#     """

#     _inherit = 'sale.order'

#     # ─────────────────────────────────────────────────────────────────────────
#     # CLM STAGE FIELD
#     # readonly=True prevents direct UI/RPC editing.
#     # Python methods (super-class or internal) can still write to it.
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_state = fields.Selection(
#         selection=[
#             ('pi', 'Proforma Invoice'),
#             ('bucket1', 'Bucket 1'),
#             ('bucket2', 'Bucket 2'),
#             ('bucket3', 'Bucket 3'),
#             ('bucket4', 'Bucket 4'),
#             ('paid', 'Paid'),
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
#     # VISIBILITY FLAGS — Computed, drive show/hide in views
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
#             # Customer acceptance button: only shown in bucket2 stage
#             order.clm_show_customer_acceptance_btn = order.clm_state == 'bucket2'

#             # Bank acceptance button: only shown after customer acceptance (bucket3 stage)
#             order.clm_show_bank_acceptance_btn = order.clm_state == 'bucket3'

#             # Payment is available only after bank acceptance (bucket4)
#             order.clm_show_payment_action = order.clm_bank_acceptance and order.clm_state == 'bucket4'

#     # ─────────────────────────────────────────────────────────────────────────
#     # FREEZE CHECK — Core enforcement method
#     # Called before every blocked operation.
#     # ─────────────────────────────────────────────────────────────────────────

#     def _clm_check_group_freeze(self, operation_label):
#         """
#         Validates the entire customer group for freeze.
#         If any member (parent or child) is frozen → raises UserError.

#         Group resolution logic:
#           - If partner has a parent_id → group_head = parent_id
#           - If partner has no parent_id → group_head = partner itself
#           - Check: group_head + all its child_ids
#         """
#         partner = self.partner_id
#         if not partner:
#             return

#         # Resolve group head
#         group_head = partner.parent_id if partner.parent_id else partner

#         # Collect all members: head + children
#         all_members = group_head | group_head.child_ids.filtered(lambda c: c.active)

#         # Find any frozen member
#         frozen_member = all_members.filtered(lambda p: p.clm_is_frozen)
#         if not frozen_member:
#             return

#         # Build detailed error from first frozen member
#         breached = frozen_member[0]
#         breach = breached.clm_get_first_breach()

#         if not breach:
#             # Freeze flag is True but no breach found (edge case) — still block
#             raise UserError(
#                 f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
#                 f"Group: {group_head.name}\n"
#                 f"Frozen Customer: {breached.name}\n"
#                 f"Please contact the Credit & Collections Manager."
#             )

#         currency = breached.currency_id
#         fmt = lambda amt: f"{currency.symbol} {amt:,.2f}"

#         raise UserError(
#             f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
#             f"Group          : {group_head.name}\n"
#             f"Frozen Customer: {breached.name}\n"
#             f"Bucket         : {breach['bucket']}\n"
#             f"Defined Limit  : {fmt(breach['limit'])}\n"
#             f"Current Exposure: {fmt(breach['exposure'])}\n"
#             f"Excess Amount  : {fmt(breach['excess'])}\n\n"
#             f"Resolve by reducing exposure or submitting a limit increase request."
#         )

#     # ─────────────────────────────────────────────────────────────────────────
#     # BLOCKED OPERATION OVERRIDES
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.model_create_multi
#     def create(self, vals_list):
#         """Block new quotation creation if customer group is frozen."""
#         orders = super().create(vals_list)
#         for order in orders:
#             if order.partner_id:
#                 order._clm_check_group_freeze('Proforma Invoice Creation')
#         return orders

#     def action_confirm(self):
#         """Block sales order confirmation if customer group is frozen."""
#         for order in self:
#             order._clm_check_group_freeze('Sales Order Confirmation')
#         return super().action_confirm()

#     # ─────────────────────────────────────────────────────────────────────────
#     # ACCEPTANCE ACTION METHODS — Called by buttons in view
#     # ─────────────────────────────────────────────────────────────────────────

#     def action_clm_customer_acceptance(self):
#         """
#         Records customer acceptance and moves stage: bucket2 → bucket3.
#         Allowed even when group is frozen (SRS §6.2 — allowed operations).
#         """
#         for order in self:
#             if order.clm_state != 'bucket2':
#                 raise UserError(
#                     f"Customer Acceptance can only be recorded when the order is in "
#                     f"'Bucket 2 — Invoiced, Awaiting Customer Acceptance'.\n"
#                     f"Current stage: {dict(order._fields['clm_state'].selection).get(order.clm_state)}"
#                 )
#             order.write({
#                 'clm_customer_acceptance': True,
#                 'clm_state': 'bucket3',
#             })

#     def action_clm_bank_acceptance(self):
#         """
#         Records bank acceptance and moves stage: bucket3 → bucket4.
#         Allowed even when group is frozen (SRS §6.2 — allowed operations).
#         """
#         for order in self:
#             if order.clm_state != 'bucket3':
#                 raise UserError(
#                     f"Bank Acceptance can only be recorded when the order is in "
#                     f"'Bucket 3 — Customer Accepted, Awaiting Bank Acceptance'.\n"
#                     f"Current stage: {dict(order._fields['clm_state'].selection).get(order.clm_state)}"
#                 )
#             order.write({
#                 'clm_bank_acceptance': True,
#                 'clm_state': 'bucket4',
#             })

#     # ─────────────────────────────────────────────────────────────────────────
#     # INTERNAL STAGE SETTERS — Called by event hooks (not directly by users)
#     # ─────────────────────────────────────────────────────────────────────────

#     def _clm_move_to_bucket1(self):
#         """Called after delivery validation. PI → Bucket 1."""
#         self.filtered(lambda o: o.clm_state == 'pi').write({'clm_state': 'bucket1'})

#     def _clm_move_to_bucket2(self):
#         """Called after invoice posting. Bucket 1 → Bucket 2."""
#         self.filtered(lambda o: o.clm_state == 'bucket1').write({'clm_state': 'bucket2'})

#     def _clm_move_to_paid(self):
#         """Called after full payment. Bucket 4 → Paid."""
#         self.filtered(lambda o: o.clm_state == 'bucket4').write({'clm_state': 'paid'})

from odoo import models, fields, api
from odoo.exceptions import UserError,AccessError


class SaleOrderExtended(models.Model):
    """
    Stage Machine — sale.order extension.

    Stage flow (automatic, driven by business events):
      pi → bucket1 (delivery validated)
      bucket1 → bucket2 (invoice posted)
      bucket2 → bucket3 (customer acceptance)
      bucket3 → bucket4 (bank acceptance)
      bucket4 → paid (full payment received)

    Users CANNOT manually change clm_state (readonly=True on field).
    Freeze check runs on: create, action_confirm, delivery validation.
    Acceptance buttons trigger stage moves on: bucket2 and bucket3.
    """

    _inherit = 'sale.order'

    # ─────────────────────────────────────────────────────────────────────────
    # CLM STAGE FIELD
    # readonly=True prevents direct UI/RPC editing.
    # Python methods (super-class or internal) can still write to it.
    # ─────────────────────────────────────────────────────────────────────────

    clm_state = fields.Selection(
        selection=[
            ('pi', 'Proforma Invoice'),
            ('bucket1', 'Bucket 1'),
            ('bucket2', 'Bucket 2'),
            ('bucket3', 'Bucket 3'),
            ('bucket4', 'Bucket 4'),
            ('paid', 'Paid'),
        ],
        string='CLM Stage',
        default='pi',
        readonly=True,
        tracking=True,
        copy=False,
        index=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # ACCEPTANCE CONTROL FIELDS
    # ─────────────────────────────────────────────────────────────────────────

    clm_customer_acceptance = fields.Boolean(
        string='Customer Acceptance',
        readonly=True,
        tracking=True,
        copy=False,
        help='Set when customer has accepted documents. Triggers move to Bucket 3.',
    )
    clm_bank_acceptance = fields.Boolean(
        string='Bank Acceptance',
        readonly=True,
        tracking=True,
        copy=False,
        help='Set when bank has accepted documents. Triggers move to Bucket 4.',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # VISIBILITY FLAGS — Computed, drive show/hide in views
    # ─────────────────────────────────────────────────────────────────────────

    clm_show_customer_acceptance_btn = fields.Boolean(
        compute='_compute_clm_visibility',
        string='Show Customer Acceptance Button',
    )
    clm_show_bank_acceptance_btn = fields.Boolean(
        compute='_compute_clm_visibility',
        string='Show Bank Acceptance Button',
    )
    clm_show_payment_action = fields.Boolean(
        compute='_compute_clm_visibility',
        string='Payment Available',
    )

    @api.depends('clm_state', 'clm_customer_acceptance', 'clm_bank_acceptance')
    def _compute_clm_visibility(self):
        for order in self:
            # Customer acceptance button: only shown in bucket2 stage
            order.clm_show_customer_acceptance_btn = order.clm_state == 'bucket2'

            # Bank acceptance button: only shown after customer acceptance (bucket3 stage)
            order.clm_show_bank_acceptance_btn = order.clm_state == 'bucket3'

            # Payment is available only after bank acceptance (bucket4)
            order.clm_show_payment_action = order.clm_bank_acceptance and order.clm_state == 'bucket4'

    # ─────────────────────────────────────────────────────────────────────────
    # FREEZE CHECK — Core enforcement method
    # Called before every blocked operation.
    # ─────────────────────────────────────────────────────────────────────────

    def _clm_check_group_freeze(self, operation_label):
        """
        Validates the entire customer group for freeze.
        If any member (parent or child) is frozen → raises UserError.

        Group resolution logic:
          - If partner has a parent_id → group_head = parent_id
          - If partner has no parent_id → group_head = partner itself
          - Check: group_head + all its child_ids
        """
        partner = self.partner_id
        if not partner:
            return

        # Resolve group head
        group_head = partner.parent_id if partner.parent_id else partner

        # Collect all members: head + children
        all_members = group_head | group_head.child_ids.filtered(lambda c: c.active)

        # Find any frozen member
        frozen_member = all_members.filtered(lambda p: p.clm_is_frozen)
        if not frozen_member:
            return

        # Build detailed error from first frozen member
        breached = frozen_member[0]
        breach = breached.clm_get_first_breach()

        if not breach:
            # Freeze flag is True but no breach found (edge case) — still block
            raise UserError(
                f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
                f"Group: {group_head.name}\n"
                f"Frozen Customer: {breached.name}\n"
                f"Please contact the Credit & Collections Manager."
            )

        currency = breached.currency_id
        fmt = lambda amt: f"{currency.symbol} {amt:,.2f}"

        raise UserError(
            f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
            f"Group          : {group_head.name}\n"
            f"Frozen Customer: {breached.name}\n"
            f"Bucket         : {breach['bucket']}\n"
            f"Defined Limit  : {fmt(breach['limit'])}\n"
            f"Current Exposure: {fmt(breach['exposure'])}\n"
            f"Excess Amount  : {fmt(breach['excess'])}\n\n"
            f"Resolve by reducing exposure or submitting a limit increase request."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCKED OPERATION OVERRIDES
    # ─────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """Block new quotation creation if customer group is frozen."""
        if not (
            self.env.user.has_group('zencore_clms.group_zencore_clm_salesperson') 
            or self.env.user.has_group('zencore_clms.group_zencore_clm_sales_manager') 
        ):
            raise AccessError("Only sales person or sales manager can create quations")
        orders = super().create(vals_list)
        for order in orders:
            if order.partner_id:
                order._clm_check_group_freeze('Proforma Invoice Creation')
        return orders

    def action_confirm(self):
        """Block sales order confirmation if customer group is frozen."""
        if not (self.env.user.has_group('zencore_clms.group_zencore_clm_sales_manager')):
            raise AccessError("Only sales manager can confirm Sales Order.")
        for order in self:
            order._clm_check_group_freeze('Sales Order Confirmation')
        return super().action_confirm()
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_tdo'):
            raise AccessError("Only TDO can create invoices.")
        
        invoices = super()._create_invoices(
            grouped=grouped,
            final=final,
            date=date
        )
        
        return invoices

    # ─────────────────────────────────────────────────────────────────────────
    # ACCEPTANCE ACTION METHODS — Called by buttons in view
    # ─────────────────────────────────────────────────────────────────────────

    def action_clm_customer_acceptance(self):
        """
        Records customer acceptance and moves stage: bucket2 → bucket3.
        Allowed even when group is frozen (SRS §6.2 — allowed operations).
        """
        if not (
            self.env.user.has_group('zencore_clms.group_zencore_clm_ccm')
            or self.env.user.has_group('zencore_clms.group_zencore_clm_salesperson')
        ):
            raise AccessError("Only CCM or Salesperson can record customer acceptance.")
        
        for order in self:
            if order.clm_state != 'bucket2':
                raise UserError(
                    f"Customer Acceptance can only be recorded when the order is in "
                    f"'Bucket 2'.\n"
                    f"Current stage: {dict(order._fields['clm_state'].selection).get(order.clm_state)}"
                )
            order.write({
                'clm_customer_acceptance': True,
                'clm_state': 'bucket3',
            })
            # order._clm_log_stage_change(
            #     from_stage='Bucket 2',
            #     to_stage='Bucket 3',
            #     trigger='Customer Acceptance Recorded',
            # )

    def action_clm_bank_acceptance(self):
        """
        Records bank acceptance and moves stage: bucket3 → bucket4.
        Allowed even when group is frozen (SRS §6.2 — allowed operations).
        """
        if not (
            self.env.user.has_group('zencore_clms.group_zencore_clm_ccm')
            or self.env.user.has_group('zencore_clms.group_zencore_clm_finance')
        ):
            raise AccessError("Only CCM or Finance can record bank acceptance.")
        
        for order in self:
            if order.clm_state != 'bucket3':
                raise UserError(
                    f"Bank Acceptance can only be recorded when the order is in "
                    f"'Bucket 3 — Customer Accepted, Awaiting Bank Acceptance'.\n"
                    f"Current stage: {dict(order._fields['clm_state'].selection).get(order.clm_state)}"
                )
            order.write({
                'clm_bank_acceptance': True,
                'clm_state': 'bucket4',
            })
            # order._clm_log_stage_change(
            #     from_stage='Bucket 3',
            #     to_stage='Bucket 4',
            #     trigger='Bank Acceptance Recorded',
            # )

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL STAGE SETTERS — Called by event hooks (not directly by users)
    # ─────────────────────────────────────────────────────────────────────────

    def _clm_move_to_bucket1(self):
        """Called after delivery validated. PI → Bucket 1."""
        orders = self.filtered(lambda o: o.clm_state == 'pi')
        orders.write({'clm_state': 'bucket1'})
        # for order in orders:
        #     order._clm_log_stage_change(
        #         from_stage='Proforma Invoice',
        #         to_stage='Bucket 1',
        #         trigger='Delivery Validated',
        #     )

    def _clm_move_to_bucket2(self):
        """Called after invoice posting. Bucket 1 → Bucket 2."""
        orders = self.filtered(lambda o: o.clm_state == 'bucket1')
        orders.write({'clm_state': 'bucket2'})
        # for order in orders:
        #     order._clm_log_stage_change(
        #         from_stage='Bucket 1',
        #         to_stage='Bucket 2',
        #         trigger='Invoice Posted',
        #     )

    def _clm_move_to_paid(self):
        """Called after full payment. Bucket 4 → Paid."""
        orders = self.filtered(lambda o: o.clm_state == 'bucket4')
        orders.write({'clm_state': 'paid'})
        # for order in orders:
        #     order._clm_log_stage_change(
        #         from_stage='Bucket 4',
        #         to_stage='Paid',
        #         trigger='Full Payment Received',
        #     )

    def _clm_log_stage_change(self, from_stage, to_stage, trigger):
        """
        Posts a structured chatter note on every stage transition.
        Uses mt_note subtype — internal audit log, no email to followers.
        """
        self.ensure_one()
        self.message_post(
            body=(
                f"CLM Stage Changed"
                f"From: {from_stage}"
                f"To: {to_stage}"
                f"Trigger: {trigger}"
                f"By: {self.env.user.name}"
            ),
            subtype_xmlid='mail.mt_note',
        )