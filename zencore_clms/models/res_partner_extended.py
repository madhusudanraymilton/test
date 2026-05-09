from odoo import models, fields, api
from odoo.exceptions import AccessError

# Fields that are ONLY writable via the approved workflow.
# Direct writes — even by admin — are blocked unless context bypass is set.
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

    Design decisions:
    ─────────────────
    - All balance fields are NON-STORED computed (always accurate, never stale).
      Uses optimised read_group() for bulk partner computation.
    - clm_is_frozen: NON-STORED — always real-time.
    - clm_group_is_frozen: NON-STORED (depends on non-stored clm_is_frozen;
      making it stored would cause ORM invalidation failure).
    - Limits are Monetary for currency consistency.
    - Parent view shows aggregated (sum of children); child view shows individual.
    - Limits are write-protected via write() override. Changes require
      clm.limit.change.request workflow (CCM → FM approval).
    """

    _inherit = 'res.partner'

    # ─────────────────────────────────────────────────────────────────────────
    # CREDIT LIMITS — Set at child customer level only
    # Direct write is blocked; only modified via approved workflow.
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
    # COMPUTED EXPOSURE BALANCES
    # Non-stored: always live, recomputed from sale.order data.
    # Uses read_group() for batch efficiency — avoids N+1 loops.
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
    # FREEZE STATUS — Real-time, non-stored
    # ─────────────────────────────────────────────────────────────────────────

    clm_is_frozen = fields.Boolean(
        string='Credit Frozen',
        compute='_compute_clm_is_frozen',
        # store=False is the default — explicitly NOT stored.
        # Rationale: storing requires clm_proforma_balance etc. to also be stored.
        # Non-stored computes depending on non-stored computes is correct ORM usage.
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PARENT-LEVEL AGGREGATED FIELDS
    # Non-stored: depends on children's non-stored computed fields.
    # FIX: clm_group_is_frozen must be NON-STORED because clm_is_frozen
    # is non-stored. Stored + non-stored dependency = stale data bug.
    # ─────────────────────────────────────────────────────────────────────────

    clm_agg_proforma_limit = fields.Monetary(
        string='Aggregated Proforma Limit',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_bucket_1_limit = fields.Monetary(
        string='Aggregated Bucket 1 Limit',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_bucket_2_limit = fields.Monetary(
        string='Aggregated Bucket 2 Limit',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_bucket_3_limit = fields.Monetary(
        string='Aggregated Bucket 3 Limit',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_bucket_4_limit = fields.Monetary(
        string='Aggregated Bucket 4 Limit',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_proforma_balance = fields.Monetary(
        string='Aggregated Proforma Balance',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_bucket_1_balance = fields.Monetary(
        string='Aggregated Bucket 1 Balance',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_bucket_2_balance = fields.Monetary(
        string='Aggregated Bucket 2 Balance',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_bucket_3_balance = fields.Monetary(
        string='Aggregated Bucket 3 Balance',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )
    clm_agg_bucket_4_balance = fields.Monetary(
        string='Aggregated Bucket 4 Balance',
        compute='_compute_clm_aggregated',
        currency_field='currency_id',
    )

    # FIX: store=False — cannot store a field that depends on a non-stored compute.
    # Original code had store=True which causes permanent staleness.
    clm_group_is_frozen = fields.Boolean(
        string='Group Frozen',
        compute='_compute_clm_aggregated',
        store=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # SQL CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    _sql_constraints = [
        ('clm_proforma_limit_positive', 'CHECK(clm_proforma_limit >= 0)',
         'Proforma Invoice Limit must be zero or positive.'),
        ('clm_bucket_1_limit_positive', 'CHECK(clm_bucket_1_limit >= 0)',
         'Bucket 1 Limit must be zero or positive.'),
        ('clm_bucket_2_limit_positive', 'CHECK(clm_bucket_2_limit >= 0)',
         'Bucket 2 Limit must be zero or positive.'),
        ('clm_bucket_3_limit_positive', 'CHECK(clm_bucket_3_limit >= 0)',
         'Bucket 3 Limit must be zero or positive.'),
        ('clm_bucket_4_limit_positive', 'CHECK(clm_bucket_4_limit >= 0)',
         'Bucket 4 Limit must be zero or positive.'),
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION — Limit fields require workflow approval
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        """
        Block direct edits to CLM limit fields.
        Only the approval workflow (clm.limit.change.request.action_approve)
        may write these via context key: clm_bypass_limit_protection=True.
        Superuser (env.su) is also blocked to prevent console bypass.
        """
        protected = _CLM_LIMIT_FIELDS & set(vals.keys())
        if protected:
            # Allow only when explicit bypass context is set by the workflow
            if not self.env.context.get('clm_bypass_limit_protection'):
                raise AccessError(
                    "Direct editing of credit limits is not permitted.\n"
                    "Submit a Limit Change Request through the CCM → FM approval workflow.\n"
                    "Fields blocked: %s" % ', '.join(sorted(protected))
                )
        return super().write(vals)

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: EXPOSURE BALANCES
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        'sale_order_ids.clm_state',
        'sale_order_ids.amount_total',
        'sale_order_ids.state',
    )
    def _compute_clm_balances(self):
        """
        Batch-compute exposure balances for all partners in self.
        Uses read_group() — single SQL query regardless of partner count.
        Only non-cancelled orders are counted.
        Only stages pi/bucket1/bucket2/bucket3/bucket4 count toward exposure.
        'paid' is intentionally excluded (exposure cleared on payment).
        """
        if not self.ids:
            for partner in self:
                partner.clm_proforma_balance = 0.0
                partner.clm_bucket_1_balance = 0.0
                partner.clm_bucket_2_balance = 0.0
                partner.clm_bucket_3_balance = 0.0
                partner.clm_bucket_4_balance = 0.0
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

        # Build lookup: {partner_id: {stage: total}}
        data = {}
        for g in groups:
            pid = g['partner_id'][0]
            stage = g['clm_state']
            data.setdefault(pid, {})[stage] = g['amount_total'] or 0.0

        for partner in self:
            pdata = data.get(partner.id, {})
            for stage, field in stage_to_field.items():
                partner[field] = pdata.get(stage, 0.0)

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: FREEZE STATUS
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
        Freeze activates when ANY configured bucket exceeds its limit.
        Limits of 0.0 = unconfigured (no freeze trigger for that bucket).
        """
        for partner in self:
            checks = [
                (partner.clm_proforma_balance, partner.clm_proforma_limit),
                (partner.clm_bucket_1_balance, partner.clm_bucket_1_limit),
                (partner.clm_bucket_2_balance, partner.clm_bucket_2_limit),
                (partner.clm_bucket_3_balance, partner.clm_bucket_3_limit),
                (partner.clm_bucket_4_balance, partner.clm_bucket_4_limit),
            ]
            partner.clm_is_frozen = any(
                balance > limit
                for balance, limit in checks
                if limit > 0.0
            )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: PARENT AGGREGATION
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        'child_ids.clm_proforma_limit',
        'child_ids.clm_bucket_1_limit',
        'child_ids.clm_bucket_2_limit',
        'child_ids.clm_bucket_3_limit',
        'child_ids.clm_bucket_4_limit',
        'child_ids.clm_proforma_balance',
        'child_ids.clm_bucket_1_balance',
        'child_ids.clm_bucket_2_balance',
        'child_ids.clm_bucket_3_balance',
        'child_ids.clm_bucket_4_balance',
        'child_ids.clm_is_frozen',
    )
    def _compute_clm_aggregated(self):
        """
        Aggregate all active child CLM data at the parent (group head) level.
        Only children with active=True are included.
        Group freeze = True if ANY child is frozen.
        """
        for partner in self:
            children = partner.child_ids.filtered(lambda c: c.active)

            partner.clm_agg_proforma_limit    = sum(children.mapped('clm_proforma_limit'))
            partner.clm_agg_bucket_1_limit    = sum(children.mapped('clm_bucket_1_limit'))
            partner.clm_agg_bucket_2_limit    = sum(children.mapped('clm_bucket_2_limit'))
            partner.clm_agg_bucket_3_limit    = sum(children.mapped('clm_bucket_3_limit'))
            partner.clm_agg_bucket_4_limit    = sum(children.mapped('clm_bucket_4_limit'))

            partner.clm_agg_proforma_balance  = sum(children.mapped('clm_proforma_balance'))
            partner.clm_agg_bucket_1_balance  = sum(children.mapped('clm_bucket_1_balance'))
            partner.clm_agg_bucket_2_balance  = sum(children.mapped('clm_bucket_2_balance'))
            partner.clm_agg_bucket_3_balance  = sum(children.mapped('clm_bucket_3_balance'))
            partner.clm_agg_bucket_4_balance  = sum(children.mapped('clm_bucket_4_balance'))

            partner.clm_group_is_frozen = any(children.mapped('clm_is_frozen'))

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITY — Used by sale.order freeze check
    # ─────────────────────────────────────────────────────────────────────────

    def clm_get_first_breach(self):
        """
        Returns details of the first breached bucket for this partner.
        Returns empty dict if no breach exists.
        Used to build the freeze error message (SRS §6.4).
        """
        self.ensure_one()
        bucket_map = [
            ('Proforma Invoice', self.clm_proforma_limit, self.clm_proforma_balance),
            ('Bucket 1',         self.clm_bucket_1_limit, self.clm_bucket_1_balance),
            ('Bucket 2',         self.clm_bucket_2_limit, self.clm_bucket_2_balance),
            ('Bucket 3',         self.clm_bucket_3_limit, self.clm_bucket_3_balance),
            ('Bucket 4',         self.clm_bucket_4_limit, self.clm_bucket_4_balance),
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
