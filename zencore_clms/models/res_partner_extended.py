from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError

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
    - All balance fields are NON-STORED computed (always accurate, never stale).
    - clm_is_frozen is also non-stored so it always reflects real-time exposure.
    - Limits are Monetary (not Char/Float) for currency consistency.
    - Parent view shows aggregated values; child view shows individual values.
    - Limits are readonly in UI — changed only via clm.limit.change.request workflow.
    """

    _inherit = 'res.partner'

    # ─────────────────────────────────────────────────────────────────────────
    # CREDIT LIMITS — Set at child customer level only (readonly in views)
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
    # COMPUTED EXPOSURE BALANCES — Real-time, system-calculated, read-only
    # These sum sale order amounts per bucket stage.
    # store=False ensures they are always recomputed from live data.
    # ─────────────────────────────────────────────────────────────────────────

    clm_proforma_balance = fields.Monetary(
        string='Proforma Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
        tracking=True,
    )
    clm_bucket_1_balance = fields.Monetary(
        string='Bucket 1 Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
        tracking=True,
    )
    clm_bucket_2_balance = fields.Monetary(
        string='Bucket 2 Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
        tracking=True,
    )
    clm_bucket_3_balance = fields.Monetary(
        string='Bucket 3 Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
        tracking=True,
    )
    clm_bucket_4_balance = fields.Monetary(
        string='Bucket 4 Balance',
        compute='_compute_clm_balances',
        currency_field='currency_id',
        tracking=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # FREEZE STATUS — Computed from balances vs limits
    # ─────────────────────────────────────────────────────────────────────────

    clm_is_frozen = fields.Boolean(
        string='Credit Frozen',
        compute='_compute_clm_is_frozen',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # PARENT-LEVEL AGGREGATED FIELDS — Read-only, sum of all children
    # ─────────────────────────────────────────────────────────────────────────

    # Aggregated Limits
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

    # Aggregated Balances
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

    # Aggregated Freeze (True if ANY child is frozen)
    clm_group_is_frozen = fields.Boolean(
        string='Group Frozen',
        compute='_compute_clm_aggregated',
    )

    #new fields
    

    def write(self, vals):
        protected = _CLM_LIMIT_FIELDS & set(vals.keys())
        if protected and not self.env.su:
            ctx = self.env.context
            if not ctx.get('clm_bypass_limit_protection'):
                raise AccessError(
                    "Direct editing of credit limits is not permitted.\n"
                    "Submit a Limit Change Request through the approval workflow."
                )
        return super().write(vals)

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE METHODS
    # ─────────────────────────────────────────────────────────────────────────

    # @api.depends(
    #     'sale_order_ids.clm_state',
    #     'sale_order_ids.amount_total',
    #     'sale_order_ids.state',
    # )
    # def _compute_clm_balances(self):
    #     """
    #     Sum sale order amounts grouped by CLM stage for this partner.
    #     Only active (non-cancelled) orders are considered.
    #     """
    #     for partner in self:
    #         active_orders = self.env['sale.order'].search([
    #             ('partner_id', '=', partner.id),
    #             ('state', 'not in', ['cancel']),
    #         ])

    #         def _sum(stage):
    #             return sum(
    #                 active_orders.filtered(lambda o: o.clm_state == stage).mapped('amount_total')
    #             )

    #         partner.clm_proforma_balance = _sum('pi')
    #         partner.clm_bucket_1_balance = _sum('bucket1')
    #         partner.clm_bucket_2_balance = _sum('bucket2')
    #         partner.clm_bucket_3_balance = _sum('bucket3')
    #         partner.clm_bucket_4_balance = _sum('bucket4')

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

        groups = self.env['sale.order'].read_group(
            domain=[
                ('partner_id', 'in', self.ids),
                ('state', '!=', 'cancel'),
            ],
            fields=['partner_id', 'clm_state', 'amount_total:sum'],
            groupby=['partner_id', 'clm_state'],
            lazy=False,
        )

        stage_to_field = {
            'pi': 'clm_proforma_balance',
            'bucket1': 'clm_bucket_1_balance',
            'bucket2': 'clm_bucket_2_balance',
            'bucket3': 'clm_bucket_3_balance',
            'bucket4': 'clm_bucket_4_balance',
        }

        data = {}
        for g in groups:
            pid = g['partner_id'][0]
            stage = g['clm_state']
            if stage in stage_to_field:
                data.setdefault(pid, {})[stage] = g['amount_total'] or 0.0

        for partner in self:
            pdata = data.get(partner.id, {})
            for stage, field in stage_to_field.items():
                partner[field] = pdata.get(stage, 0.0)

    @api.depends(
        'clm_proforma_balance', 'clm_proforma_limit',
        'clm_bucket_1_balance', 'clm_bucket_1_limit',
        'clm_bucket_2_balance', 'clm_bucket_2_limit',
        'clm_bucket_3_balance', 'clm_bucket_3_limit',
        'clm_bucket_4_balance', 'clm_bucket_4_limit',
    )
    def _compute_clm_is_frozen(self):
        """
        Freeze is active when ANY bucket exposure exceeds its limit.
        Limits of 0.0 are treated as unconfigured (no freeze trigger).
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
                if limit > 0.0  # skip unconfigured limits
            )

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
        Aggregate all child customer CLM data at the parent (group head) level.
        Only active children are included.
        """
        for partner in self:
            children = partner.child_ids.filtered(lambda c: c.active)

            partner.clm_agg_proforma_limit = sum(children.mapped('clm_proforma_limit'))
            partner.clm_agg_bucket_1_limit = sum(children.mapped('clm_bucket_1_limit'))
            partner.clm_agg_bucket_2_limit = sum(children.mapped('clm_bucket_2_limit'))
            partner.clm_agg_bucket_3_limit = sum(children.mapped('clm_bucket_3_limit'))
            partner.clm_agg_bucket_4_limit = sum(children.mapped('clm_bucket_4_limit'))

            partner.clm_agg_proforma_balance = sum(children.mapped('clm_proforma_balance'))
            partner.clm_agg_bucket_1_balance = sum(children.mapped('clm_bucket_1_balance'))
            partner.clm_agg_bucket_2_balance = sum(children.mapped('clm_bucket_2_balance'))
            partner.clm_agg_bucket_3_balance = sum(children.mapped('clm_bucket_3_balance'))
            partner.clm_agg_bucket_4_balance = sum(children.mapped('clm_bucket_4_balance'))

            partner.clm_group_is_frozen = any(children.mapped('clm_is_frozen'))

    # ─────────────────────────────────────────────────────────────────────────
    # UTILITY — Used by sale.order freeze check
    # ─────────────────────────────────────────────────────────────────────────

    def clm_get_first_breach(self):
        """
        Returns a dict describing the first breached bucket for this partner.
        Used to build the freeze error message.
        """
        self.ensure_one()
        BUCKET_MAP = [
            ('Proforma Invoice', self.clm_proforma_limit, self.clm_proforma_balance),
            ('Bucket 1', self.clm_bucket_1_limit, self.clm_bucket_1_balance),
            ('Bucket 2', self.clm_bucket_2_limit, self.clm_bucket_2_balance),
            ('Bucket 3', self.clm_bucket_3_limit, self.clm_bucket_3_balance),
            ('Bucket 4', self.clm_bucket_4_limit, self.clm_bucket_4_balance),
        ]
        for bucket_name, limit, balance in BUCKET_MAP:
            if limit > 0.0 and balance > limit:
                return {
                    'bucket': bucket_name,
                    'limit': limit,
                    'exposure': balance,
                    'excess': balance - limit,
                }
        return {}