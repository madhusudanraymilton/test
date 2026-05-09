from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError

# Fields that must NEVER be written directly by users.
# Stage machine controls these exclusively.
_CLM_PROTECTED_FIELDS = frozenset({
    'clm_state',
    'clm_customer_acceptance',
    'clm_bank_acceptance',
})


class SaleOrderExtended(models.Model):
    """
    CLM Stage Machine — sale.order extension.

    Stage flow (automatic, driven by business events only):
      pi → bucket1      : delivery validated         (stock_picking_extended)
      bucket1 → bucket2 : invoice posted             (account_move_extended)
      bucket2 → bucket3 : customer acceptance button (action_clm_customer_acceptance)
      bucket3 → bucket4 : bank acceptance button     (action_clm_bank_acceptance)
      bucket4 → paid    : full payment received      (account_move_extended)

    Freeze enforcement (SRS §6.2):
      BLOCKED: create, action_confirm, delivery validation
      ALLOWED: invoice posting, customer acceptance, bank acceptance, payment

    SoD enforcement (SRS §10):
      create         → Salesperson OR Sales Manager
      action_confirm → Sales Manager only
      delivery       → Warehouse only (in stock_picking_extended)
      invoice create → TDO only (in _create_invoices)
      invoice post   → TDO only (in account_move_extended)
      payment        → Finance only (in account_move_extended)
    """

    _inherit = 'sale.order'

    # ─────────────────────────────────────────────────────────────────────────
    # CLM STAGE FIELD
    # ─────────────────────────────────────────────────────────────────────────

    clm_state = fields.Selection(
        selection=[
            ('pi',      'Proforma Invoice'),
            ('bucket1', 'Bucket 1'),
            ('bucket2', 'Bucket 2'),
            ('bucket3', 'Bucket 3'),
            ('bucket4', 'Bucket 4'),
            ('paid',    'Paid'),
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
    # readonly=True on field definition; only internal methods write these.
    # write() override below provides a second enforcement layer against RPC.
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
    # VISIBILITY FLAGS — Drive show/hide in views
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
            order.clm_show_customer_acceptance_btn = (
                order.clm_state == 'bucket2' and not order.clm_customer_acceptance
            )
            order.clm_show_bank_acceptance_btn = (
                order.clm_state == 'bucket3' and not order.clm_bank_acceptance
            )
            order.clm_show_payment_action = (
                order.clm_bank_acceptance and order.clm_state == 'bucket4'
            )

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION — Prevent RPC bypass of stage machine
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        """
        Block direct writes to CLM stage/acceptance fields from external callers.
        Internal methods use with_context(clm_internal_write=True).
        This prevents JSON-RPC bypass of the stage machine.
        """
        protected = _CLM_PROTECTED_FIELDS & set(vals.keys())
        if protected and not self.env.context.get('clm_internal_write'):
            raise AccessError(
                "CLM stage fields cannot be modified directly.\n"
                "Stage transitions are controlled by business events only.\n"
                "Fields blocked: %s" % ', '.join(sorted(protected))
            )
        return super().write(vals)

    # ─────────────────────────────────────────────────────────────────────────
    # FREEZE CHECK — Core group-level enforcement
    # ─────────────────────────────────────────────────────────────────────────

    def _clm_check_group_freeze(self, operation_label):
        """
        Validates the entire customer group for freeze before any blocked operation.
        SRS §7 — group-wide enforcement: if ANY child is frozen, ALL are blocked.

        Group resolution:
          child partner → group_head = partner.parent_id
          standalone    → group_head = partner itself
          All children of group_head are checked.

        Raises UserError with full breach details (SRS §6.4 / §7.10).
        """
        partner = self.partner_id
        if not partner:
            return

        # Resolve group head (one level — Odoo contacts are typically 2-level)
        group_head = partner.parent_id if partner.parent_id else partner

        # Collect all group members: head + all active children
        all_members = group_head | group_head.child_ids.filtered(lambda c: c.active)

        # Find first frozen member
        frozen_members = all_members.filtered(lambda p: p.clm_is_frozen)
        if not frozen_members:
            return

        breached = frozen_members[0]
        breach = breached.clm_get_first_breach()

        currency = breached.currency_id
        fmt = lambda amt: f"{currency.symbol} {amt:,.2f}"

        if not breach:
            raise UserError(
                f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
                f"Group           : {group_head.name}\n"
                f"Frozen Customer : {breached.name}\n\n"
                f"Contact the Credit & Collections Manager to resolve."
            )

        raise UserError(
            f"⛔  Credit Freeze — '{operation_label}' Blocked\n\n"
            f"Group           : {group_head.name}\n"
            f"Frozen Customer : {breached.name}\n"
            f"Bucket          : {breach['bucket']}\n"
            f"Defined Limit   : {fmt(breach['limit'])}\n"
            f"Current Exposure: {fmt(breach['exposure'])}\n"
            f"Excess Amount   : {fmt(breach['excess'])}\n\n"
            f"Resolution: reduce exposure or submit a Limit Increase Request (CCM → FM)."
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCKED OPERATION OVERRIDES (SRS §6.2)
    # ─────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """
        SoD: Only Salesperson or Sales Manager can create quotations.
        Freeze: Block creation if customer group is frozen (SRS §6.2).
        """
        if not (
            self.env.user.has_group('zencore_clms.group_zencore_clm_salesperson')
            or self.env.user.has_group('zencore_clms.group_zencore_clm_sales_manager')
        ):
            raise AccessError(
                "Only Salesperson or Sales Manager can create quotations."
            )

        # Force clm_state = 'pi' on all new records (prevent external injection)
        for vals in vals_list:
            vals['clm_state'] = 'pi'

        orders = super().create(vals_list)
        for order in orders:
            if order.partner_id:
                order._clm_check_group_freeze('Proforma Invoice Creation')
        return orders

    def action_confirm(self):
        """
        SoD: Only Sales Manager can confirm a Sales Order.
        Freeze: Block confirmation if customer group is frozen (SRS §6.2).
        """
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_sales_manager'):
            raise AccessError("Only Sales Manager can confirm a Sales Order.")
        for order in self:
            order._clm_check_group_freeze('Sales Order Confirmation')
        return super().action_confirm()

    def _create_invoices(self, grouped=False, final=False, date=None):
        """
        SoD: Only TDO can create invoices (SRS §10).
        No freeze check — invoice creation is ALLOWED even when frozen (SRS §6.2).
        """
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_tdo'):
            raise AccessError(
                "Only TDO (Territory/Technical Delivery Officer) can create invoices."
            )
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    # ─────────────────────────────────────────────────────────────────────────
    # ACCEPTANCE ACTIONS — Called by buttons, not by users directly
    # ─────────────────────────────────────────────────────────────────────────

    def action_clm_customer_acceptance(self):
        """
        Records customer acceptance → moves stage: Bucket 2 → Bucket 3.
        SRS §4.1: Allowed even when frozen (SRS §6.2).
        SoD: CCM or Salesperson may record.
        """
        if not (
            self.env.user.has_group('zencore_clms.group_zencore_clm_ccm')
            or self.env.user.has_group('zencore_clms.group_zencore_clm_salesperson')
        ):
            raise AccessError(
                "Only CCM or Salesperson can record Customer Acceptance."
            )
        for order in self:
            if order.clm_state != 'bucket2':
                stage_label = dict(order._fields['clm_state'].selection).get(order.clm_state)
                raise UserError(
                    f"Customer Acceptance requires order to be in Bucket 2.\n"
                    f"Current stage: {stage_label}"
                )
            order.with_context(clm_internal_write=True).write({
                'clm_customer_acceptance': True,
                'clm_state': 'bucket3',
            })
            order._clm_log_stage_change(
                from_stage='Bucket 2',
                to_stage='Bucket 3',
                trigger='Customer Acceptance Recorded',
            )

    def action_clm_bank_acceptance(self):
        """
        Records bank acceptance → moves stage: Bucket 3 → Bucket 4.
        SRS §4.2: Allowed even when frozen (SRS §6.2).
        SoD: CCM or Finance may record.
        """
        if not (
            self.env.user.has_group('zencore_clms.group_zencore_clm_ccm')
            or self.env.user.has_group('zencore_clms.group_zencore_clm_finance')
        ):
            raise AccessError(
                "Only CCM or Finance can record Bank Acceptance."
            )
        for order in self:
            if order.clm_state != 'bucket3':
                stage_label = dict(order._fields['clm_state'].selection).get(order.clm_state)
                raise UserError(
                    f"Bank Acceptance requires order to be in Bucket 3.\n"
                    f"Current stage: {stage_label}"
                )
            order.with_context(clm_internal_write=True).write({
                'clm_bank_acceptance': True,
                'clm_state': 'bucket4',
            })
            order._clm_log_stage_change(
                from_stage='Bucket 3',
                to_stage='Bucket 4',
                trigger='Bank Acceptance Recorded',
            )

    # ─────────────────────────────────────────────────────────────────────────
    # INTERNAL STAGE SETTERS — Called by event hooks only
    # All use clm_internal_write=True to bypass the write() guard.
    # ─────────────────────────────────────────────────────────────────────────

    def _clm_move_to_bucket1(self):
        """Delivery validated → PI → Bucket 1 (SRS §3.2)."""
        orders = self.filtered(lambda o: o.clm_state == 'pi')
        if orders:
            orders.with_context(clm_internal_write=True).write({'clm_state': 'bucket1'})
            for order in orders:
                order._clm_log_stage_change(
                    from_stage='Proforma Invoice',
                    to_stage='Bucket 1',
                    trigger='Delivery Validated',
                )

    def _clm_move_to_bucket2(self):
        """Invoice posted → Bucket 1 → Bucket 2 (SRS §3.3)."""
        orders = self.filtered(lambda o: o.clm_state == 'bucket1')
        if orders:
            orders.with_context(clm_internal_write=True).write({'clm_state': 'bucket2'})
            for order in orders:
                order._clm_log_stage_change(
                    from_stage='Bucket 1',
                    to_stage='Bucket 2',
                    trigger='Invoice Posted',
                )

    def _clm_move_to_paid(self):
        """Full payment received → Bucket 4 → Paid (SRS §3.6)."""
        orders = self.filtered(
            lambda o: o.clm_state == 'bucket4' and o.clm_bank_acceptance
        )
        if orders:
            orders.with_context(clm_internal_write=True).write({'clm_state': 'paid'})
            for order in orders:
                order._clm_log_stage_change(
                    from_stage='Bucket 4',
                    to_stage='Paid',
                    trigger='Full Payment Received',
                )

    # ─────────────────────────────────────────────────────────────────────────
    # AUDIT LOGGING — Chatter note on every stage transition
    # ─────────────────────────────────────────────────────────────────────────

    def _clm_log_stage_change(self, from_stage, to_stage, trigger):
        """
        Posts a structured chatter note on every CLM stage transition.
        Uses mt_note subtype — internal audit only, no email to followers.
        """
        self.ensure_one()
        self.message_post(
            body=(
                f"Stage Transition"
                f"From  : {from_stage}"
                f"To    : {to_stage}"
                f"Trigger: {trigger}"
                f"By    : {self.env.user.name}"
            ),
            subtype_xmlid='mail.mt_note',
        )
