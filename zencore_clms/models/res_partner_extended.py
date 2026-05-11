from odoo import models, fields, api
from odoo.exceptions import AccessError,ValidationError, UserError

_CLM_LIMIT_FIELDS = frozenset({
    'clm_proforma_limit',
    'clm_bucket_1_limit',
    'clm_bucket_2_limit',
    'clm_bucket_3_limit',
    'clm_bucket_4_limit',
})


class ResPartnerExtended(models.Model):
    """
    Credit Engine — res.partner extension.

    Freeze Architecture (SRS §3.3 / §3.4):
    ────────────────────────────────────────
    clm_is_frozen        : individual breach — does THIS partner exceed any OWN limit?
    bucket_freeze_active : group-aware freeze — True if this partner OR any group
                           member (group_head + all active children) has clm_is_frozen.

    Group definition:
      child partner  → group_head = partner.parent_id
      standalone     → group_head = partner itself
      group_head     → group = self + all active child_ids

    When ANY member breaches → bucket_freeze_active = True for ALL members.
    This is the field used for all freeze enforcement and UI display.

    clm_group_is_frozen is DEPRECATED — replaced by bucket_freeze_active.
    Retained for backward compat on parent-level aggregated views only.
    """

    _inherit = 'res.partner'

    # ─────────────────────────────────────────────────────────────────────────
    # CREDIT LIMITS
    # ─────────────────────────────────────────────────────────────────────────

    clm_proforma_limit = fields.Monetary(
        string='Proforma Invoice Limit',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    clm_bucket_1_limit = fields.Monetary(
        string='Bucket 1 Limit',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    clm_bucket_2_limit = fields.Monetary(
        string='Bucket 2 Limit',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    clm_bucket_3_limit = fields.Monetary(
        string='Bucket 3 Limit',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )
    clm_bucket_4_limit = fields.Monetary(
        string='Bucket 4 Limit',
        currency_field='currency_id',
        default=0.0,
        tracking=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTED EXPOSURE BALANCES — Non-stored, always live
    # ─────────────────────────────────────────────────────────────────────────

    clm_proforma_balance = fields.Monetary(
        string='Proforma Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
    )
    clm_bucket_1_balance = fields.Monetary(
        string='Bucket 1 Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
    )
    clm_bucket_2_balance = fields.Monetary(
        string='Bucket 2 Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
    )
    clm_bucket_3_balance = fields.Monetary(
        string='Bucket 3 Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
    )
    clm_bucket_4_balance = fields.Monetary(
        string='Bucket 4 Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # FREEZE STATUS
    # ─────────────────────────────────────────────────────────────────────────

    clm_is_frozen = fields.Boolean(
        string='Own Limit Breached',
        compute='_compute_clm_is_frozen',
        store=False,
        help=(
            'True if THIS partner personally exceeds any configured bucket limit.\n'
            'Does NOT include group siblings. Use bucket_freeze_active for enforcement.'
        ),
    )

    bucket_freeze_active = fields.Boolean(
        # ── SRS §3.4 canonical freeze field ──────────────────────────────────
        # True when: this partner OR any member of their credit group breaches
        # any individual bucket limit.
        #
        # @api.depends covers:
        #   - own breach        : clm_is_frozen
        #   - parent's breach   : parent_id.clm_is_frozen
        #   - sibling breach    : parent_id.child_ids.clm_is_frozen
        #   - child breach      : child_ids.clm_is_frozen
        #
        # All four paths are required because:
        #   child partner  → needs parent + sibling paths
        #   group head     → needs own + child paths
        #   standalone     → needs only own path
        string='Credit Freeze Active',
        compute='_compute_bucket_freeze_active',
        store=False,
        help=(
            'True if this partner or any member of their credit group\n'
            'has exceeded a bucket limit. Blocks PI creation, SO confirmation,\n'
            'and delivery validation for ALL group members simultaneously.\n'
            'Never blocks invoicing, acceptances, or payment registration.'
        ),
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PARENT-LEVEL AGGREGATED FIELDS — Non-stored
    # ─────────────────────────────────────────────────────────────────────────

    clm_agg_proforma_limit   = fields.Monetary(string='Aggregated Proforma Limit',   compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_1_limit   = fields.Monetary(string='Aggregated Bucket 1 Limit',   compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_2_limit   = fields.Monetary(string='Aggregated Bucket 2 Limit',   compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_3_limit   = fields.Monetary(string='Aggregated Bucket 3 Limit',   compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_4_limit   = fields.Monetary(string='Aggregated Bucket 4 Limit',   compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_proforma_balance = fields.Monetary(string='Aggregated Proforma Balance', compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_1_balance = fields.Monetary(string='Aggregated Bucket 1 Balance', compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_2_balance = fields.Monetary(string='Aggregated Bucket 2 Balance', compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_3_balance = fields.Monetary(string='Aggregated Bucket 3 Balance', compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_4_balance = fields.Monetary(string='Aggregated Bucket 4 Balance', compute='_compute_clm_aggregated', currency_field='currency_id')

    # clm_group_is_frozen: retained for parent-level UI only.
    # For enforcement → always use bucket_freeze_active.
    clm_group_is_frozen = fields.Boolean(
        string='Group Frozen (any member)',
        compute='_compute_clm_aggregated',
        store=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # LIMIT CHANGE REQUEST INTEGRATION
    # One definition only — FIX: previous code had duplicate field declaration.
    # ─────────────────────────────────────────────────────────────────────────

    clm_limit_request_ids = fields.One2many(
        'clm.limit.change.request',
        'partner_id',
        string='All Limit Requests',
    )

    clm_active_request_ids = fields.One2many(
        'clm.limit.change.request',
        'partner_id',
        string='Active Requests',
        domain=[('state', 'in', ('draft', 'pending_fm'))],
    )

    clm_request_total_count   = fields.Integer(string='Total Requests',   compute='_compute_clm_request_counts')
    clm_request_pending_count = fields.Integer(string='Pending Requests', compute='_compute_clm_request_counts')
    clm_request_approved_count = fields.Integer(string='Approved Requests', compute='_compute_clm_request_counts')
    clm_request_rejected_count = fields.Integer(string='Rejected Requests', compute='_compute_clm_request_counts')

    clm_pending_request_id            = fields.Many2one('clm.limit.change.request', compute='_compute_pending_request', store=False)
    clm_pending_request_state         = fields.Char(compute='_compute_pending_request', store=False)
    clm_pending_request_ref           = fields.Char(compute='_compute_pending_request', store=False)
    clm_pending_request_type          = fields.Char(compute='_compute_pending_request', store=False)
    clm_pending_request_initiated_by  = fields.Char(compute='_compute_pending_request', store=False)

    # ─────────────────────────────────────────────────────────────────────────
    # SQL CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    _sql_constraints = [
        ('clm_proforma_limit_positive', 'CHECK(clm_proforma_limit >= 0)', 'Proforma Limit must be zero or positive.'),
        ('clm_bucket_1_limit_positive', 'CHECK(clm_bucket_1_limit >= 0)', 'Bucket 1 Limit must be zero or positive.'),
        ('clm_bucket_2_limit_positive', 'CHECK(clm_bucket_2_limit >= 0)', 'Bucket 2 Limit must be zero or positive.'),
        ('clm_bucket_3_limit_positive', 'CHECK(clm_bucket_3_limit >= 0)', 'Bucket 3 Limit must be zero or positive.'),
        ('clm_bucket_4_limit_positive', 'CHECK(clm_bucket_4_limit >= 0)', 'Bucket 4 Limit must be zero or positive.'),
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        protected = _CLM_LIMIT_FIELDS & set(vals.keys())
        if protected and not self.env.context.get('clm_bypass_limit_protection'):
            raise AccessError(
                "Direct editing of credit limits is not permitted.\n"
                "Submit a Limit Change Request through the CCM → FM approval workflow.\n"
                "Fields blocked: %s" % ', '.join(sorted(protected))
            )
        return super().write(vals)

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: EXPOSURE BALANCES
    # Single read_group() — O(1) SQL regardless of partner count
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        'sale_order_ids.clm_state',
        'sale_order_ids.amount_total',
        'sale_order_ids.state',
    )
    def _compute_clm_balances(self):
        if not self.ids:
            for p in self:
                p.clm_proforma_balance = p.clm_bucket_1_balance = p.clm_bucket_2_balance = 0.0
                p.clm_bucket_3_balance = p.clm_bucket_4_balance = 0.0
            return

        stage_to_field = {
            'pi':      'clm_proforma_balance',
            'bucket1': 'clm_bucket_1_balance',
            'bucket2': 'clm_bucket_2_balance',
            'bucket3': 'clm_bucket_3_balance',
            'bucket4': 'clm_bucket_4_balance',
        }

        groups = self.env['sale.order'].read_group(
            domain=[
                ('partner_id', 'in', self.ids),
                ('state', 'not in', ['cancel']),
                ('clm_state', 'in', list(stage_to_field.keys())),
            ],
            fields=['partner_id', 'clm_state', 'amount_total:sum'],
            groupby=['partner_id', 'clm_state'],
            lazy=False,
        )

        data = {}
        for g in groups:
            pid   = g['partner_id'][0]
            stage = g['clm_state']
            data.setdefault(pid, {})[stage] = g['amount_total'] or 0.0

        for partner in self:
            pdata = data.get(partner.id, {})
            for stage, field in stage_to_field.items():
                partner[field] = pdata.get(stage, 0.0)

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: INDIVIDUAL FREEZE — does THIS partner personally breach any limit?
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        'clm_proforma_balance', 'clm_proforma_limit',
        'clm_bucket_1_balance', 'clm_bucket_1_limit',
        'clm_bucket_2_balance', 'clm_bucket_2_limit',
        'clm_bucket_3_balance', 'clm_bucket_3_limit',
        'clm_bucket_4_balance', 'clm_bucket_4_limit',
    )
    def _compute_clm_is_frozen(self):
        """
        True when this partner's own exposure exceeds any configured (non-zero) limit.
        A limit of 0.0 = unconfigured → never triggers a freeze for that bucket.
        This is the PER-PARTNER breach detector — not the group enforcement field.
        Use bucket_freeze_active for all freeze enforcement logic.
        """
        for partner in self:
            pairs = [
                (partner.clm_proforma_balance, partner.clm_proforma_limit),
                (partner.clm_bucket_1_balance, partner.clm_bucket_1_limit),
                (partner.clm_bucket_2_balance, partner.clm_bucket_2_limit),
                (partner.clm_bucket_3_balance, partner.clm_bucket_3_limit),
                (partner.clm_bucket_4_balance, partner.clm_bucket_4_limit),
            ]
            partner.clm_is_frozen = any(
                balance > limit
                for balance, limit in pairs
                if limit > 0.0          # 0.0 = unconfigured, skip
            )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: GROUP FREEZE — SRS §3.4 bucket_freeze_active
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        # Own breach
        'clm_is_frozen',
        # Parent's own breach (covers group head when self is a child)
        'parent_id',
        'parent_id.clm_is_frozen',
        # Sibling breach (via group head → sibling path)
        'parent_id.child_ids.clm_is_frozen',
        # Child breach (covers group head computing its own freeze)
        'child_ids.clm_is_frozen',
    )
    def _compute_bucket_freeze_active(self):
        """
        SRS §3.4 — Group-wide freeze propagation.

        Algorithm:
          1. Resolve the group head:
               child partner  → group_head = partner.parent_id
               standalone     → group_head = partner itself
               group head     → group_head = partner itself

          2. Collect ALL group members:
               group_head + all active child_ids of group_head

          3. If ANY member's clm_is_frozen is True → bucket_freeze_active = True
             for ALL members (propagated in step 4).

          4. Set result on each partner in self.

        Why we loop over `all_members` explicitly rather than using any():
          We need to set the field on every partner in `self`. For partners that
          share a group, the ORM may batch them together or compute them
          separately depending on cache state. Resolving group membership per
          record is correct and predictable.

        Performance: Non-stored compute. Odoo only recomputes when the depends
        fields change. For large partner sets the group resolution is O(n)
        with one extra ORM lookup per unique group_head — acceptable given the
        business context (credit managers, not mass batch jobs).
        """
        for partner in self:
            # ── Step 1: Resolve group head ────────────────────────────────
            group_head = partner.parent_id if partner.parent_id else partner

            # ── Step 2: Collect all group members ────────────────────────
            # Include group head itself + all active children of group head.
            # Inactive partners are excluded (archived entities should not
            # contribute to or be blocked by the group freeze).
            all_members = group_head | group_head.child_ids.filtered(
                lambda c: c.active
            )

            # ── Step 3: Any member frozen → whole group frozen ────────────
            partner.bucket_freeze_active = any(
                m.clm_is_frozen for m in all_members
            )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: PARENT AGGREGATION
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        'child_ids.clm_proforma_limit',  'child_ids.clm_bucket_1_limit',
        'child_ids.clm_bucket_2_limit',  'child_ids.clm_bucket_3_limit',
        'child_ids.clm_bucket_4_limit',
        'child_ids.clm_proforma_balance', 'child_ids.clm_bucket_1_balance',
        'child_ids.clm_bucket_2_balance', 'child_ids.clm_bucket_3_balance',
        'child_ids.clm_bucket_4_balance',
        # FIX: also depend on OWN balance/limit so that when the group head
        # itself breaches a limit, clm_group_is_frozen updates correctly.
        'clm_is_frozen',
        'child_ids.clm_is_frozen',
    )
    def _compute_clm_aggregated(self):
        """
        Aggregate credit data for group head (parent) partners.

        BUG FIX (previous version):
          clm_group_is_frozen was computed as:
            any(children.mapped('clm_is_frozen'))
          This MISSED the case where the group head itself breaches a limit.
          If Acme Corp (parent) exceeds its own bucket limit, clm_group_is_frozen
          would return False because no child was frozen.

          Fix: include the partner's OWN clm_is_frozen in the check.
          clm_group_is_frozen = partner.clm_is_frozen OR any child is frozen.

        Note: For enforcement, always use bucket_freeze_active (which already
        handles this correctly for all partner types). clm_group_is_frozen is
        retained only for the aggregated view on parent partner forms.
        """
        for partner in self:
            children = partner.child_ids.filtered(lambda c: c.active)

            partner.clm_agg_proforma_limit   = sum(children.mapped('clm_proforma_limit'))
            partner.clm_agg_bucket_1_limit   = sum(children.mapped('clm_bucket_1_limit'))
            partner.clm_agg_bucket_2_limit   = sum(children.mapped('clm_bucket_2_limit'))
            partner.clm_agg_bucket_3_limit   = sum(children.mapped('clm_bucket_3_limit'))
            partner.clm_agg_bucket_4_limit   = sum(children.mapped('clm_bucket_4_limit'))
            partner.clm_agg_proforma_balance = sum(children.mapped('clm_proforma_balance'))
            partner.clm_agg_bucket_1_balance = sum(children.mapped('clm_bucket_1_balance'))
            partner.clm_agg_bucket_2_balance = sum(children.mapped('clm_bucket_2_balance'))
            partner.clm_agg_bucket_3_balance = sum(children.mapped('clm_bucket_3_balance'))
            partner.clm_agg_bucket_4_balance = sum(children.mapped('clm_bucket_4_balance'))

            # FIX: include own freeze + any child freeze
            partner.clm_group_is_frozen = (
                partner.clm_is_frozen
                or any(children.mapped('clm_is_frozen'))
            )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: REQUEST STATISTICS
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('clm_limit_request_ids.state')
    def _compute_clm_request_counts(self):
        if not self.ids:
            for p in self:
                p.clm_request_total_count = p.clm_request_pending_count = 0
                p.clm_request_approved_count = p.clm_request_rejected_count = 0
            return

        groups = self.env['clm.limit.change.request']._read_group(
            domain=[('partner_id', 'in', self.ids)],
            groupby=['partner_id', 'state'],
            aggregates=['__count'],
        )

        data = {}
        for partner_rec, state, count in groups:
            data.setdefault(partner_rec.id, {})[state] = count

        for partner in self:
            pdata = data.get(partner.id, {})
            partner.clm_request_total_count    = sum(pdata.values())
            partner.clm_request_pending_count  = pdata.get('pending_fm', 0)
            partner.clm_request_approved_count = pdata.get('approved', 0)
            partner.clm_request_rejected_count = pdata.get('rejected', 0)

    @api.depends(
        'clm_limit_request_ids.state',
        'clm_limit_request_ids.name',
        'clm_limit_request_ids.request_type',
        'clm_limit_request_ids.initiated_by',
    )
    def _compute_pending_request(self):
        for partner in self:
            active = partner.clm_limit_request_ids.filtered(
                lambda r: r.state in ('draft', 'pending_fm')
            ).sorted('create_date', reverse=True)

            if active:
                req = active[0]
                partner.clm_pending_request_id           = req
                partner.clm_pending_request_state        = req.state
                partner.clm_pending_request_ref          = req.name
                partner.clm_pending_request_type         = dict(req._fields['request_type'].selection).get(req.request_type, '')
                partner.clm_pending_request_initiated_by = req.initiated_by.name or ''
            else:
                partner.clm_pending_request_id           = False
                partner.clm_pending_request_state        = ''
                partner.clm_pending_request_ref          = ''
                partner.clm_pending_request_type         = ''
                partner.clm_pending_request_initiated_by = ''

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITY
    # ─────────────────────────────────────────────────────────────────────────

    def clm_get_first_breach(self):
        """
        Returns breach details for the first bucket where balance > limit.
        Used by sale_order._clm_check_group_freeze() to build the error message.
        Returns empty dict if no breach exists.
        """
        self.ensure_one()
        bucket_map = [
            ('Proforma Invoice', self.clm_proforma_limit, self.clm_proforma_balance),
            ('Bucket 1 — Delivered, Not Invoiced',           self.clm_bucket_1_limit, self.clm_bucket_1_balance),
            ('Bucket 2 — Invoiced, Awaiting Customer Accept', self.clm_bucket_2_limit, self.clm_bucket_2_balance),
            ('Bucket 3 — Customer Accepted, Awaiting Bank',   self.clm_bucket_3_limit, self.clm_bucket_3_balance),
            ('Bucket 4 — Bank Accepted, Payment Pending',     self.clm_bucket_4_limit, self.clm_bucket_4_balance),
        ]
        for bucket_name, limit, balance in bucket_map:
            if limit > 0.0 and balance > limit:
                return {
                    'bucket':   bucket_name,
                    'limit':    limit,
                    'exposure': balance,
                    'excess':   balance - limit,
                }
        return {}

    # ─────────────────────────────────────────────────────────────────────────
    # PARTNER-LEVEL LIMIT REQUEST ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def action_view_limit_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Limit Requests — {self.name}',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_view_pending_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pending Requests — {self.name}',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id), ('state', '=', 'pending_fm')],
            'context': {'default_partner_id': self.id},
        }

    def action_clm_new_limit_request(self):
        self.ensure_one()
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_ccm'):
            raise AccessError("Only CCM can submit limit change requests.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
        }

    def action_clm_view_pending_request(self):
        self.ensure_one()
        active_ids = self.clm_limit_request_ids.filtered(
            lambda r: r.state in ('draft', 'pending_fm')
        ).ids
        if not active_ids:
            raise UserError("No active limit change requests found for this customer.")
        return {
            'type': 'ir.actions.act_window',
            'name': f'Active Requests — {self.name}',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', active_ids)],
            'context': {'default_partner_id': self.id},
        }

    def action_clm_approve_limit_request(self):
        self.ensure_one()
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
            raise AccessError("Only Finance can approve limit change requests.")
        pending = self.clm_limit_request_ids.filtered(lambda r: r.state == 'pending_fm')
        if not pending:
            raise UserError("No pending limit change requests found for this customer.")
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pending Requests — {self.name}',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pending.ids)],
            'context': {'default_partner_id': self.id},
        }

    def action_clm_reject_limit_request(self):
        self.ensure_one()
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
            raise AccessError("Only Finance can reject limit change requests.")
        pending = self.clm_limit_request_ids.filtered(lambda r: r.state == 'pending_fm')
        if not pending:
            raise UserError("No pending limit change requests found for this customer.")
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pending Requests — {self.name}',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pending.ids)],
            'context': {'default_partner_id': self.id, 'clm_reject_mode': True},
        }