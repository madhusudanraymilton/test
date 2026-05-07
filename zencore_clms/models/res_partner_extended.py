# from odoo import models, fields

# class ResPartnerExtended(models.Model):
#     _inherit = 'res.partner'

#     clm_bucket_1_limit = fields.Char(string='Bucket 1 limit') 
#     clm_bucket_2_limit = fields.Char(string='Bucket 2 limit') 
#     clm_bucket_3_limit = fields.Char(string='Bucket 3 limit') 
#     clm_bucket_4_limit = fields.Char(string='Bucket 4 limit')

#     clm_bucket_1_balance = fields.Float(string='Bucket 1 balance')
#     clm_bucket_2_balance = fields.Float(string='Bucket 2 balance')
#     clm_bucket_3_balance = fields.Float(string='Bucket 3 balance')
#     clm_bucket_4_balance = fields.Float(string='Bucket 4 balance')

from odoo import models, fields, api


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
        string='Proforma Exposure Limit',
        currency_field='currency_id',
        default=0.0,
    )
    clm_bucket_1_limit = fields.Monetary(
        string='Bucket 1 Limit',
        currency_field='currency_id',
        default=0.0,
    )
    clm_bucket_2_limit = fields.Monetary(
        string='Bucket 2 Limit',
        currency_field='currency_id',
        default=0.0,
    )
    clm_bucket_3_limit = fields.Monetary(
        string='Bucket 3 Limit',
        currency_field='currency_id',
        default=0.0,
    )
    clm_bucket_4_limit = fields.Monetary(
        string='Bucket 4 Limit',
        currency_field='currency_id',
        default=0.0,
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

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE METHODS
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        'sale_order_ids.clm_state',
        'sale_order_ids.amount_total',
        'sale_order_ids.state',
    )
    def _compute_clm_balances(self):
        """
        Sum sale order amounts grouped by CLM stage for this partner.
        Only active (non-cancelled) orders are considered.
        """
        for partner in self:
            active_orders = self.env['sale.order'].search([
                ('partner_id', '=', partner.id),
                ('state', 'not in', ['cancel']),
            ])

            def _sum(stage):
                return sum(
                    active_orders.filtered(lambda o: o.clm_state == stage).mapped('amount_total')
                )

            partner.clm_proforma_balance = _sum('pi')
            partner.clm_bucket_1_balance = _sum('bucket1')
            partner.clm_bucket_2_balance = _sum('bucket2')
            partner.clm_bucket_3_balance = _sum('bucket3')
            partner.clm_bucket_4_balance = _sum('bucket4')

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
            ('Bucket 1 — Delivered, Not Invoiced', self.clm_bucket_1_limit, self.clm_bucket_1_balance),
            ('Bucket 2 — Invoiced, Awaiting Customer Acceptance', self.clm_bucket_2_limit, self.clm_bucket_2_balance),
            ('Bucket 3 — Customer Accepted, Awaiting Bank Acceptance', self.clm_bucket_3_limit, self.clm_bucket_3_balance),
            ('Bucket 4 — Bank Accepted, Payment Pending', self.clm_bucket_4_limit, self.clm_bucket_4_balance),
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