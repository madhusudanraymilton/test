# from odoo import models, fields, api
# from odoo.exceptions import AccessError

# # Fields that are ONLY writable via the approved workflow.
# # Direct writes — even by admin — are blocked unless context bypass is set.
# _CLM_LIMIT_FIELDS = frozenset({
#     'clm_proforma_limit',
#     'clm_bucket_1_limit',
#     'clm_bucket_2_limit',
#     'clm_bucket_3_limit',
#     'clm_bucket_4_limit',
# })


# class ResPartnerExtended(models.Model):
#     """
#     Credit Engine — res.partner extension.

#     Design decisions:
#     ─────────────────
#     - All balance fields are NON-STORED computed (always accurate, never stale).
#       Uses optimised read_group() for bulk partner computation.
#     - clm_is_frozen: NON-STORED — always real-time.
#     - clm_group_is_frozen: NON-STORED (depends on non-stored clm_is_frozen;
#       making it stored would cause ORM invalidation failure).
#     - Limits are Monetary for currency consistency.
#     - Parent view shows aggregated (sum of children); child view shows individual.
#     - Limits are write-protected via write() override. Changes require
#       clm.limit.change.request workflow (CCM → FM approval).
#     """

#     _inherit = 'res.partner'

#     # ─────────────────────────────────────────────────────────────────────────
#     # CREDIT LIMITS — Set at child customer level only
#     # Direct write is blocked; only modified via approved workflow.
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_proforma_limit = fields.Monetary(
#         string='Proforma Invoice Limit',
#         currency_field='currency_id',
#         default=0.0,
#         tracking=True,
#     )
#     clm_bucket_1_limit = fields.Monetary(
#         string='Bucket 1 Limit',
#         currency_field='currency_id',
#         default=0.0,
#         tracking=True,
#     )
#     clm_bucket_2_limit = fields.Monetary(
#         string='Bucket 2 Limit',
#         currency_field='currency_id',
#         default=0.0,
#         tracking=True,
#     )
#     clm_bucket_3_limit = fields.Monetary(
#         string='Bucket 3 Limit',
#         currency_field='currency_id',
#         default=0.0,
#         tracking=True,
#     )
#     clm_bucket_4_limit = fields.Monetary(
#         string='Bucket 4 Limit',
#         currency_field='currency_id',
#         default=0.0,
#         tracking=True,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # COMPUTED EXPOSURE BALANCES
#     # Non-stored: always live, recomputed from sale.order data.
#     # Uses read_group() for batch efficiency — avoids N+1 loops.
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_proforma_balance = fields.Monetary(
#         string='Proforma Balance',
#         compute='_compute_clm_balances',
#         currency_field='currency_id',
#     )
#     clm_bucket_1_balance = fields.Monetary(
#         string='Bucket 1 Balance',
#         compute='_compute_clm_balances',
#         currency_field='currency_id',
#     )
#     clm_bucket_2_balance = fields.Monetary(
#         string='Bucket 2 Balance',
#         compute='_compute_clm_balances',
#         currency_field='currency_id',
#     )
#     clm_bucket_3_balance = fields.Monetary(
#         string='Bucket 3 Balance',
#         compute='_compute_clm_balances',
#         currency_field='currency_id',
#     )
#     clm_bucket_4_balance = fields.Monetary(
#         string='Bucket 4 Balance',
#         compute='_compute_clm_balances',
#         currency_field='currency_id',
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # FREEZE STATUS — Real-time, non-stored
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_is_frozen = fields.Boolean(
#         string='Credit Frozen',
#         compute='_compute_clm_is_frozen',
#         # store=False is the default — explicitly NOT stored.
#         # Rationale: storing requires clm_proforma_balance etc. to also be stored.
#         # Non-stored computes depending on non-stored computes is correct ORM usage.
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # PARENT-LEVEL AGGREGATED FIELDS
#     # Non-stored: depends on children's non-stored computed fields.
#     # FIX: clm_group_is_frozen must be NON-STORED because clm_is_frozen
#     # is non-stored. Stored + non-stored dependency = stale data bug.
#     # ─────────────────────────────────────────────────────────────────────────

#     clm_agg_proforma_limit = fields.Monetary(
#         string='Aggregated Proforma Limit',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_bucket_1_limit = fields.Monetary(
#         string='Aggregated Bucket 1 Limit',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_bucket_2_limit = fields.Monetary(
#         string='Aggregated Bucket 2 Limit',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_bucket_3_limit = fields.Monetary(
#         string='Aggregated Bucket 3 Limit',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_bucket_4_limit = fields.Monetary(
#         string='Aggregated Bucket 4 Limit',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_proforma_balance = fields.Monetary(
#         string='Aggregated Proforma Balance',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_bucket_1_balance = fields.Monetary(
#         string='Aggregated Bucket 1 Balance',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_bucket_2_balance = fields.Monetary(
#         string='Aggregated Bucket 2 Balance',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_bucket_3_balance = fields.Monetary(
#         string='Aggregated Bucket 3 Balance',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )
#     clm_agg_bucket_4_balance = fields.Monetary(
#         string='Aggregated Bucket 4 Balance',
#         compute='_compute_clm_aggregated',
#         currency_field='currency_id',
#     )

#     # FIX: store=False — cannot store a field that depends on a non-stored compute.
#     # Original code had store=True which causes permanent staleness.
#     clm_group_is_frozen = fields.Boolean(
#         string='Group Frozen',
#         compute='_compute_clm_aggregated',
#         store=False,
#     )

#     # ─────────────────────────────────────────────────────────────────────────
#     # SQL CONSTRAINTS
#     # ─────────────────────────────────────────────────────────────────────────

#     _sql_constraints = [
#         ('clm_proforma_limit_positive', 'CHECK(clm_proforma_limit >= 0)',
#          'Proforma Invoice Limit must be zero or positive.'),
#         ('clm_bucket_1_limit_positive', 'CHECK(clm_bucket_1_limit >= 0)',
#          'Bucket 1 Limit must be zero or positive.'),
#         ('clm_bucket_2_limit_positive', 'CHECK(clm_bucket_2_limit >= 0)',
#          'Bucket 2 Limit must be zero or positive.'),
#         ('clm_bucket_3_limit_positive', 'CHECK(clm_bucket_3_limit >= 0)',
#          'Bucket 3 Limit must be zero or positive.'),
#         ('clm_bucket_4_limit_positive', 'CHECK(clm_bucket_4_limit >= 0)',
#          'Bucket 4 Limit must be zero or positive.'),
#     ]

#     # ─────────────────────────────────────────────────────────────────────────
#     # WRITE PROTECTION — Limit fields require workflow approval
#     # ─────────────────────────────────────────────────────────────────────────

#     def write(self, vals):
#         """
#         Block direct edits to CLM limit fields.
#         Only the approval workflow (clm.limit.change.request.action_approve)
#         may write these via context key: clm_bypass_limit_protection=True.
#         Superuser (env.su) is also blocked to prevent console bypass.
#         """
#         protected = _CLM_LIMIT_FIELDS & set(vals.keys())
#         if protected:
#             # Allow only when explicit bypass context is set by the workflow
#             if not self.env.context.get('clm_bypass_limit_protection'):
#                 raise AccessError(
#                     "Direct editing of credit limits is not permitted.\n"
#                     "Submit a Limit Change Request through the CCM → FM approval workflow.\n"
#                     "Fields blocked: %s" % ', '.join(sorted(protected))
#                 )
#         return super().write(vals)

#     # ─────────────────────────────────────────────────────────────────────────
#     # COMPUTE: EXPOSURE BALANCES
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.depends(
#         'sale_order_ids.clm_state',
#         'sale_order_ids.amount_total',
#         'sale_order_ids.state',
#     )
#     def _compute_clm_balances(self):
#         """
#         Batch-compute exposure balances for all partners in self.
#         Uses read_group() — single SQL query regardless of partner count.
#         Only non-cancelled orders are counted.
#         Only stages pi/bucket1/bucket2/bucket3/bucket4 count toward exposure.
#         'paid' is intentionally excluded (exposure cleared on payment).
#         """
#         if not self.ids:
#             for partner in self:
#                 partner.clm_proforma_balance = 0.0
#                 partner.clm_bucket_1_balance = 0.0
#                 partner.clm_bucket_2_balance = 0.0
#                 partner.clm_bucket_3_balance = 0.0
#                 partner.clm_bucket_4_balance = 0.0
#             return

#         stage_to_field = {
#             'pi':      'clm_proforma_balance',
#             'bucket1': 'clm_bucket_1_balance',
#             'bucket2': 'clm_bucket_2_balance',
#             'bucket3': 'clm_bucket_3_balance',
#             'bucket4': 'clm_bucket_4_balance',
#         }

#         groups = self.env['sale.order'].read_group(
#             domain=[
#                 ('partner_id', 'in', self.ids),
#                 ('state', 'not in', ['cancel']),
#                 ('clm_state', 'in', list(stage_to_field.keys())),
#             ],
#             fields=['partner_id', 'clm_state', 'amount_total:sum'],
#             groupby=['partner_id', 'clm_state'],
#             lazy=False,
#         )

#         # Build lookup: {partner_id: {stage: total}}
#         data = {}
#         for g in groups:
#             pid = g['partner_id'][0]
#             stage = g['clm_state']
#             data.setdefault(pid, {})[stage] = g['amount_total'] or 0.0

#         for partner in self:
#             pdata = data.get(partner.id, {})
#             for stage, field in stage_to_field.items():
#                 partner[field] = pdata.get(stage, 0.0)

#     # ─────────────────────────────────────────────────────────────────────────
#     # COMPUTE: FREEZE STATUS
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.depends(
#         'clm_proforma_balance', 'clm_proforma_limit',
#         'clm_bucket_1_balance', 'clm_bucket_1_limit',
#         'clm_bucket_2_balance', 'clm_bucket_2_limit',
#         'clm_bucket_3_balance', 'clm_bucket_3_limit',
#         'clm_bucket_4_balance', 'clm_bucket_4_limit',
#     )
#     def _compute_clm_is_frozen(self):
#         """
#         Freeze activates when ANY configured bucket exceeds its limit.
#         Limits of 0.0 = unconfigured (no freeze trigger for that bucket).
#         """
#         for partner in self:
#             checks = [
#                 (partner.clm_proforma_balance, partner.clm_proforma_limit),
#                 (partner.clm_bucket_1_balance, partner.clm_bucket_1_limit),
#                 (partner.clm_bucket_2_balance, partner.clm_bucket_2_limit),
#                 (partner.clm_bucket_3_balance, partner.clm_bucket_3_limit),
#                 (partner.clm_bucket_4_balance, partner.clm_bucket_4_limit),
#             ]
#             partner.clm_is_frozen = any(
#                 balance > limit
#                 for balance, limit in checks
#                 if limit > 0.0
#             )

#     # ─────────────────────────────────────────────────────────────────────────
#     # COMPUTE: PARENT AGGREGATION
#     # ─────────────────────────────────────────────────────────────────────────

#     @api.depends(
#         'child_ids.clm_proforma_limit',
#         'child_ids.clm_bucket_1_limit',
#         'child_ids.clm_bucket_2_limit',
#         'child_ids.clm_bucket_3_limit',
#         'child_ids.clm_bucket_4_limit',
#         'child_ids.clm_proforma_balance',
#         'child_ids.clm_bucket_1_balance',
#         'child_ids.clm_bucket_2_balance',
#         'child_ids.clm_bucket_3_balance',
#         'child_ids.clm_bucket_4_balance',
#         'child_ids.clm_is_frozen',
#     )
#     def _compute_clm_aggregated(self):
#         """
#         Aggregate all active child CLM data at the parent (group head) level.
#         Only children with active=True are included.
#         Group freeze = True if ANY child is frozen.
#         """
#         for partner in self:
#             children = partner.child_ids.filtered(lambda c: c.active)

#             partner.clm_agg_proforma_limit    = sum(children.mapped('clm_proforma_limit'))
#             partner.clm_agg_bucket_1_limit    = sum(children.mapped('clm_bucket_1_limit'))
#             partner.clm_agg_bucket_2_limit    = sum(children.mapped('clm_bucket_2_limit'))
#             partner.clm_agg_bucket_3_limit    = sum(children.mapped('clm_bucket_3_limit'))
#             partner.clm_agg_bucket_4_limit    = sum(children.mapped('clm_bucket_4_limit'))

#             partner.clm_agg_proforma_balance  = sum(children.mapped('clm_proforma_balance'))
#             partner.clm_agg_bucket_1_balance  = sum(children.mapped('clm_bucket_1_balance'))
#             partner.clm_agg_bucket_2_balance  = sum(children.mapped('clm_bucket_2_balance'))
#             partner.clm_agg_bucket_3_balance  = sum(children.mapped('clm_bucket_3_balance'))
#             partner.clm_agg_bucket_4_balance  = sum(children.mapped('clm_bucket_4_balance'))

#             partner.clm_group_is_frozen = any(children.mapped('clm_is_frozen'))

#     # ─────────────────────────────────────────────────────────────────────────
#     # UTILITY — Used by sale.order freeze check
#     # ─────────────────────────────────────────────────────────────────────────

#     def clm_get_first_breach(self):
#         """
#         Returns details of the first breached bucket for this partner.
#         Returns empty dict if no breach exists.
#         Used to build the freeze error message (SRS §6.4).
#         """
#         self.ensure_one()
#         bucket_map = [
#             ('Proforma Invoice', self.clm_proforma_limit, self.clm_proforma_balance),
#             ('Bucket 1',         self.clm_bucket_1_limit, self.clm_bucket_1_balance),
#             ('Bucket 2',         self.clm_bucket_2_limit, self.clm_bucket_2_balance),
#             ('Bucket 3',         self.clm_bucket_3_limit, self.clm_bucket_3_balance),
#             ('Bucket 4',         self.clm_bucket_4_limit, self.clm_bucket_4_balance),
#         ]
#         for bucket_name, limit, balance in bucket_map:
#             if limit > 0.0 and balance > limit:
#                 return {
#                     'bucket':   bucket_name,
#                     'limit':    limit,
#                     'exposure': balance,
#                     'excess':   balance - limit,
#                 }
#         return {}

from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError

# Fields that are ONLY writable via the approved workflow.
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

    v0.6.0 changes:
    ────────────────
    - clm_limit_request_ids    : One2many to clm.limit.change.request
    - clm_limit_request_count  : smart button counter (all requests)
    - clm_pending_request_id   : computed — most recent draft/pending_fm request
    - clm_pending_request_state: computed char — drives view invisible attrs
    - action_view_limit_requests()     : smart button target
    - action_clm_new_limit_request()   : CCM opens/creates a request
    - action_clm_view_pending_request(): view existing draft/pending in dialog
    - action_clm_approve_limit_request(): Finance approves inline
    - action_clm_reject_limit_request() : Finance opens request form for comment+reject

    Design:
    ────────
    The separate CLM menu is removed. All limit management is driven from
    this partner form's Credit Management tab and smart button.
    clm.limit.change.request model is kept for audit trail — it is just no
    longer accessible from a standalone menu item.
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
    # FREEZE STATUS — Real-time, non-stored
    # ─────────────────────────────────────────────────────────────────────────

    clm_is_frozen = fields.Boolean(
        string='Credit Frozen',
        compute='_compute_clm_is_frozen',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PARENT-LEVEL AGGREGATED FIELDS — Non-stored
    # ─────────────────────────────────────────────────────────────────────────

    clm_agg_proforma_limit    = fields.Monetary(string='Aggregated Proforma Limit',    compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_1_limit    = fields.Monetary(string='Aggregated Bucket 1 Limit',    compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_2_limit    = fields.Monetary(string='Aggregated Bucket 2 Limit',    compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_3_limit    = fields.Monetary(string='Aggregated Bucket 3 Limit',    compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_4_limit    = fields.Monetary(string='Aggregated Bucket 4 Limit',    compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_proforma_balance  = fields.Monetary(string='Aggregated Proforma Balance',  compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_1_balance  = fields.Monetary(string='Aggregated Bucket 1 Balance',  compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_2_balance  = fields.Monetary(string='Aggregated Bucket 2 Balance',  compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_3_balance  = fields.Monetary(string='Aggregated Bucket 3 Balance',  compute='_compute_clm_aggregated', currency_field='currency_id')
    clm_agg_bucket_4_balance  = fields.Monetary(string='Aggregated Bucket 4 Balance',  compute='_compute_clm_aggregated', currency_field='currency_id')

    clm_group_is_frozen = fields.Boolean(
        string='Group Frozen',
        compute='_compute_clm_aggregated',
        store=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # LIMIT CHANGE REQUEST INTEGRATION
    # ─────────────────────────────────────────────────────────────────────────

    clm_limit_request_ids = fields.One2many(
        'clm.limit.change.request',
        'partner_id',
        string='Limit Change Requests',
    )

    clm_limit_request_count = fields.Integer(
        string='Limit Requests',
        compute='_compute_limit_request_count',
    )

    clm_pending_request_id = fields.Many2one(
        'clm.limit.change.request',
        string='Active Limit Request',
        compute='_compute_pending_request',
        store=False,
        help='Most recent non-terminal (draft or pending_fm) limit change request.',
    )

    clm_pending_request_state = fields.Char(
        string='Active Request State',
        compute='_compute_pending_request',
        store=False,
        help=(
            'State of the active limit request. Used by view invisible attrs.\n'
            'Values: draft | pending_fm | (empty string when no active request)'
        ),
    )

    clm_pending_request_ref = fields.Char(
        string='Active Request Reference',
        compute='_compute_pending_request',
        store=False,
    )

    clm_pending_request_type = fields.Char(
        string='Active Request Type',
        compute='_compute_pending_request',
        store=False,
    )

    clm_pending_request_initiated_by = fields.Char(
        string='Submitted By',
        compute='_compute_pending_request',
        store=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # SQL CONSTRAINTS
    # ─────────────────────────────────────────────────────────────────────────

    _sql_constraints = [
        ('clm_proforma_limit_positive', 'CHECK(clm_proforma_limit >= 0)',   'Proforma Invoice Limit must be zero or positive.'),
        ('clm_bucket_1_limit_positive', 'CHECK(clm_bucket_1_limit >= 0)',   'Bucket 1 Limit must be zero or positive.'),
        ('clm_bucket_2_limit_positive', 'CHECK(clm_bucket_2_limit >= 0)',   'Bucket 2 Limit must be zero or positive.'),
        ('clm_bucket_3_limit_positive', 'CHECK(clm_bucket_3_limit >= 0)',   'Bucket 3 Limit must be zero or positive.'),
        ('clm_bucket_4_limit_positive', 'CHECK(clm_bucket_4_limit >= 0)',   'Bucket 4 Limit must be zero or positive.'),
    ]

     # All requests — used for smart button (total count) and history list
    clm_limit_request_ids = fields.One2many(
        'clm.limit.change.request',
        'partner_id',
        string='All Limit Requests',
    )

    # Active requests only — used for the Credit Management tab embedded list
    # domain= on One2many filters what is displayed (Odoo 17+ behaviour)
    clm_active_request_ids = fields.One2many(
        'clm.limit.change.request',
        'partner_id',
        string='Active Requests',
        domain=[('state', 'in', ('draft', 'pending_fm'))],
    )

    # ── Statistics (computed via _read_group — one SQL query for all four) ──

    clm_request_total_count = fields.Integer(
        string='Total Requests',
        compute='_compute_clm_request_counts',
    )
    clm_request_pending_count = fields.Integer(
        string='Pending Requests',
        compute='_compute_clm_request_counts',
    )
    clm_request_approved_count = fields.Integer(
        string='Approved Requests',
        compute='_compute_clm_request_counts',
    )
    clm_request_rejected_count = fields.Integer(
        string='Rejected Requests',
        compute='_compute_clm_request_counts',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: REQUEST STATISTICS
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('clm_limit_request_ids.state')
    def _compute_clm_request_counts(self):
        """
        Batch-compute all four request counts in ONE SQL query.

        Uses _read_group (Odoo 17+ / 19 API — replaces read_group).
        Returns tuples: (partner_record, state_str, count_int).

        Falls back to zero for partners with no requests.
        """
        if not self.ids:
            for p in self:
                p.clm_request_total_count = 0
                p.clm_request_pending_count = 0
                p.clm_request_approved_count = 0
                p.clm_request_rejected_count = 0
            return

        # _read_group: Odoo 19 standard — returns list of tuples
        groups = self.env['clm.limit.change.request']._read_group(
            domain=[('partner_id', 'in', self.ids)],
            groupby=['partner_id', 'state'],
            aggregates=['__count'],
        )

        # data[partner_id][state] = count
        data = {}
        for partner_rec, state, count in groups:
            data.setdefault(partner_rec.id, {})[state] = count

        for partner in self:
            pdata = data.get(partner.id, {})
            partner.clm_request_total_count   = sum(pdata.values())
            partner.clm_request_pending_count = pdata.get('pending_fm', 0)
            partner.clm_request_approved_count = pdata.get('approved', 0)
            partner.clm_request_rejected_count = pdata.get('rejected', 0)

    # ─────────────────────────────────────────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def action_view_limit_requests(self):
        """
        Smart button → ALL requests for this customer (all states).
        """
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
        """
        Smart button → PENDING requests for this customer.
        Primarily useful for Finance quick-access.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pending Requests — {self.name}',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'list,form',
            'domain': [
                ('partner_id', '=', self.id),
                ('state', '=', 'pending_fm'),
            ],
            'context': {'default_partner_id': self.id},
        }

    def action_clm_new_limit_request(self):
        """
        CCM: Opens a new limit change request form in a dialog.

        If a draft request already exists for this customer, opens it
        (prevents creating another draft for the same customer when buckets
        from the previous draft are still unclaimed).

        Note: Multiple PENDING requests for different buckets are allowed —
        this only deduplicates unsubmitted drafts.

        SoD: CCM group only. Also enforced in ClmLimitChangeRequest.create().
        """
        self.ensure_one()
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_ccm'):
            raise AccessError("Only CCM can submit limit change requests.")

        # Find the most recent unsubmitted draft for this partner
        existing_draft = self.env['clm.limit.change.request'].search([
            ('partner_id', '=', self.id),
            ('state', '=', 'draft'),
        ], limit=1, order='create_date desc')

        if existing_draft:
            # Open the existing draft rather than create a duplicate
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'clm.limit.change.request',
                'res_id': existing_draft.id,
                'view_mode': 'form',
                'target': 'new',
                'name': f'Edit Draft — {existing_draft.name}',
            }

        # No existing draft — open a blank form pre-filled with this partner
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'form',
            'target': 'new',
            'name': 'New Limit Change Request',
            'context': {'default_partner_id': self.id},
        }

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE PROTECTION — Limit fields require workflow approval
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        protected = _CLM_LIMIT_FIELDS & set(vals.keys())
        if protected:
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
        'child_ids.clm_proforma_limit',  'child_ids.clm_bucket_1_limit',
        'child_ids.clm_bucket_2_limit',  'child_ids.clm_bucket_3_limit',
        'child_ids.clm_bucket_4_limit',  'child_ids.clm_proforma_balance',
        'child_ids.clm_bucket_1_balance','child_ids.clm_bucket_2_balance',
        'child_ids.clm_bucket_3_balance','child_ids.clm_bucket_4_balance',
        'child_ids.clm_is_frozen',
    )
    def _compute_clm_aggregated(self):
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
            partner.clm_group_is_frozen       = any(children.mapped('clm_is_frozen'))

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE: LIMIT REQUEST TRACKING
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('clm_limit_request_ids')
    def _compute_limit_request_count(self):
        """Total count of all limit requests (all states) for the smart button."""
        for partner in self:
            partner.clm_limit_request_count = len(partner.clm_limit_request_ids)

    @api.depends(
        'clm_limit_request_ids.state',
        'clm_limit_request_ids.name',
        'clm_limit_request_ids.request_type',
        'clm_limit_request_ids.initiated_by',
    )
    def _compute_pending_request(self):
        """
        Identifies the most recent non-terminal (draft or pending_fm) request.

        Why Char for clm_pending_request_state instead of Selection:
          view `invisible` attrs in Odoo 19 evaluate against the actual Python
          value. A Selection field returns False when empty, but a Char field
          returns '' (empty string). Using Char is more predictable with
          invisible="clm_pending_request_state == 'pending_fm'" patterns.

        Why store=False:
          These depend on the non-stored One2many state — storing them
          would require a trigger that Odoo cannot reliably invalidate.
        """
        for partner in self:
            # Sort by create_date descending → most recent first
            active = partner.clm_limit_request_ids.filtered(
                lambda r: r.state in ('draft', 'pending_fm')
            ).sorted('create_date', reverse=True)

            if active:
                req = active[0]
                partner.clm_pending_request_id            = req
                partner.clm_pending_request_state         = req.state
                partner.clm_pending_request_ref           = req.name
                partner.clm_pending_request_type          = (
                    dict(req._fields['request_type'].selection).get(req.request_type, '')
                )
                partner.clm_pending_request_initiated_by  = req.initiated_by.name or ''
            else:
                partner.clm_pending_request_id            = False
                partner.clm_pending_request_state         = ''
                partner.clm_pending_request_ref           = ''
                partner.clm_pending_request_type          = ''
                partner.clm_pending_request_initiated_by  = ''

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITY — Used by sale.order freeze check
    # ─────────────────────────────────────────────────────────────────────────

    def clm_get_first_breach(self):
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

    # ─────────────────────────────────────────────────────────────────────────
    # PARTNER-LEVEL LIMIT REQUEST ACTIONS
    # These proxy to clm.limit.change.request methods.
    # All open as dialogs (target='new') to keep the user on the partner form.
    # ─────────────────────────────────────────────────────────────────────────

    def action_view_limit_requests(self):
        """
        Smart button: opens ALL limit change requests for this partner.
        Accessible by CCM, Finance, Sales Manager (group restriction in view).
        """
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'name':      f'Limit Requests — {self.name}',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'list,form',
            'domain':    [('partner_id', '=', self.id)],
            'context':   {'default_partner_id': self.id},
        }

    def action_clm_new_limit_request(self):
        """
        CCM: Opens a new limit change request form for this partner in a dialog.

        Behaviour:
          - If an active draft/pending_fm request already exists, opens that
            request instead (prevents duplicates).
          - If no active request, opens a blank new form pre-filled with partner.
          - Always opens as target='new' (dialog) so the user stays on the partner.

        SoD: CCM group only. Enforced here AND in clm.limit.change.request.create().
        """
        self.ensure_one()
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_ccm'):
            raise AccessError("Only CCM can submit limit change requests.")

        if self.clm_pending_request_id:
            # Open the existing active request — do not create a duplicate
            return {
                'type':      'ir.actions.act_window',
                'res_model': 'clm.limit.change.request',
                'res_id':    self.clm_pending_request_id.id,
                'view_mode': 'form',
                'target':    'new',
            }

        return {
            'type':      'ir.actions.act_window',
            'res_model': 'clm.limit.change.request',
            'view_mode': 'form',
            'target':    'new',
            'context': {
                'default_partner_id': self.id,
            },
        }

    def action_clm_view_pending_request(self):
        """
        Opens the active pending request in a dialog (read-only for non-CCM).
        Available to all roles that can see the Credit Management tab.
        """
        self.ensure_one()
        if not self.clm_pending_request_id:
            raise UserError("No active limit change request found for this customer.")
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'clm.limit.change.request',
            'res_id':    self.clm_pending_request_id.id,
            'view_mode': 'form',
            'target':    'new',
        }

    def action_clm_approve_limit_request(self):
        """
        Finance: Directly approves the active pending_fm request from the partner form.

        Why direct (not dialog):
          Approve has no required input (no comment needed) — a single click
          with a confirm dialog in the view is enough for Finance to approve.
          The chatter note is written by action_approve() on the request model.

        SoD: Finance group only. Enforced here AND in clm.limit.change.request.action_approve().
        """
        self.ensure_one()
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
            raise AccessError("Only Finance can approve limit change requests.")

        request = self.clm_pending_request_id
        if not request:
            raise UserError("No active limit change request found for this customer.")
        if request.state != 'pending_fm':
            raise UserError(
                f"Request {request.name} is in state '{request.state}'. "
                f"Only 'Pending FM' requests can be approved."
            )

        request.action_approve()

        # Invalidate partner-level computed fields so the view refreshes
        self.invalidate_recordset([
            'clm_pending_request_id',
            'clm_pending_request_state',
            'clm_pending_request_ref',
        ])

    def action_clm_reject_limit_request(self):
        """
        Finance: Opens the pending request form in a dialog so Finance can enter
        the required FM comment and click Reject from within the request form.

        Why dialog (not direct):
          Reject REQUIRES an FM comment (enforced in action_reject()).
          The cleanest UX is to open the request form where the fm_comment
          field is visible and the Reject button is already present.
          This avoids duplicating validation logic here.

        SoD: Finance group only.
        """
        self.ensure_one()
        if not self.env.user.has_group('zencore_clms.group_zencore_clm_finance'):
            raise AccessError("Only Finance can reject limit change requests.")

        request = self.clm_pending_request_id
        if not request:
            raise UserError("No active limit change request found for this customer.")
        if request.state != 'pending_fm':
            raise UserError(
                f"Request {request.name} is in state '{request.state}'. "
                f"Only 'Pending FM' requests can be rejected."
            )

        return {
            'type':      'ir.actions.act_window',
            'res_model': 'clm.limit.change.request',
            'res_id':    request.id,
            'view_mode': 'form',
            'target':    'new',
            'context':   {'clm_reject_mode': True},
        }