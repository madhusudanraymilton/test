# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AssetStatusDashboard(models.TransientModel):
    """
    Transient model that powers the Asset Status Dashboard.
    The wizard lets the user pick a product (or an existing registered asset)
    and then shows live KPI cards for every lifecycle state.
    """
    _name = 'asset.status.dashboard'
    _description = 'Asset Status Dashboard'

    # ── Filters ───────────────────────────────────────────────────────────────

    product_id = fields.Many2one(
        'product.product',
        string='Asset Product',
        domain="[('is_asset', '=', True)]",
        help='Filter the dashboard to a single product. Leave empty to see all assets.',
    )
    asset_id = fields.Many2one(
        'account.asset',
        string='Specific Asset',
        domain="[('lot_id', '!=', False), ('asset_state', '!=', 'draft')]",
        help='Drill down to a single registered asset.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # ── Read-only KPI fields (computed on-the-fly) ────────────────────────────

    count_draft = fields.Integer(compute='_compute_counts', string='Draft')
    count_available = fields.Integer(compute='_compute_counts', string='Available')
    count_assigned = fields.Integer(compute='_compute_counts', string='Assigned')
    count_scrapped = fields.Integer(compute='_compute_counts', string='Scrapped')
    count_disposed = fields.Integer(compute='_compute_counts', string='Disposed')
    count_total = fields.Integer(compute='_compute_counts', string='Total')

    @api.depends('product_id', 'asset_id', 'company_id')
    def _compute_counts(self):
        for rec in self:
            domain = rec._base_domain()
            assets = self.env['account.asset'].sudo().search(domain)
            rec.count_draft = sum(1 for a in assets if a.asset_state == 'draft')
            rec.count_available = sum(1 for a in assets if a.asset_state == 'available')
            rec.count_assigned = sum(1 for a in assets if a.asset_state == 'assigned')
            rec.count_scrapped = sum(1 for a in assets if a.asset_state == 'scrapped')
            rec.count_disposed = sum(1 for a in assets if a.asset_state == 'disposed')
            rec.count_total = len(assets)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _base_domain(self):
        """Build the search domain based on the current wizard filters."""
        domain = [('company_id', '=', self.company_id.id)]
        if self.asset_id:
            domain.append(('id', '=', self.asset_id.id))
        elif self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
            domain.append(('lot_id', '!=', False))
        else:
            # All registered + draft assets for this company
            pass
        return domain

    # ── Navigation actions ────────────────────────────────────────────────────

    def _open_assets_by_state(self, state):
        """Return a window action filtered to the given asset_state."""
        self.ensure_one()
        domain = self._base_domain()
        if state == 'draft':
            # Draft assets may not have lot_id yet
            domain.append(('asset_state', '=', 'draft'))
        elif state == 'scrapped_disposed':
            domain.append(('asset_state', 'in', ['scrapped', 'disposed']))
        else:
            domain.append(('asset_state', '=', state))
            domain.append(('lot_id', '!=', False))

        state_labels = {
            'draft': 'Draft Assets',
            'available': 'Available Assets',
            'assigned': 'Assigned Assets',
            'scrapped': 'Scrapped Assets',
            'disposed': 'Disposed Assets',
            'scrapped_disposed': 'Scrapped / Disposed Assets',
        }
        name = state_labels.get(state, 'Assets')

        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'account.asset',
            'view_mode': 'list,kanban,form',
            'domain': domain,
            'target': 'current',
        }

    def action_open_draft(self):
        return self._open_assets_by_state('draft')

    def action_open_available(self):
        return self._open_assets_by_state('available')

    def action_open_assigned(self):
        return self._open_assets_by_state('assigned')

    def action_open_scrapped(self):
        return self._open_assets_by_state('scrapped')

    def action_open_disposed(self):
        return self._open_assets_by_state('disposed')

    def action_open_all(self):
        self.ensure_one()
        domain = self._base_domain()
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Assets',
            'res_model': 'account.asset',
            'view_mode': 'list,kanban,form',
            'domain': domain,
            'target': 'current',
        }

    # ── RPC method called by the OWL client action ────────────────────────────

    @api.model
    def get_status_dashboard_data(self, product_id=None, asset_id=None, company_id=None):
        """
        Called from the OWL AssetStatusDashboard component via orm.call().
        Returns all KPI + asset-list data needed to render the dashboard.
        """
        company = self.env['res.company'].browse(company_id) if company_id else self.env.company

        domain = [('company_id', '=', company.id)]
        if asset_id:
            domain.append(('id', '=', asset_id))
        elif product_id:
            domain.append(('product_id', '=', product_id))

        assets = self.env['account.asset'].sudo().search(domain, order='code asc')

        # ── Counts per state ─────────────────────────────────────────────────
        states = ['draft', 'available', 'assigned', 'scrapped', 'disposed']
        counts = {s: 0 for s in states}
        for a in assets:
            if a.asset_state in counts:
                counts[a.asset_state] += 1

        # ── Financial totals (active assets only) ─────────────────────────────
        active = assets.filtered(lambda a: a.asset_state in ('available', 'assigned'))
        total_value = sum(active.mapped('original_value'))
        net_book_value = sum(active.mapped('value_residual'))
        total_depreciated = total_value - net_book_value

        # ── Recent activity (last 15 history events) ──────────────────────────
        history_domain = [('company_id', '=', company.id)]
        if asset_id:
            history_domain.append(('asset_id', '=', asset_id))
        elif product_id:
            history_domain.append(('asset_id.product_id', '=', product_id))

        recent_history = self.env['asset.history'].sudo().search(
            history_domain,
            order='event_date desc',
            limit=15,
        )
        history_rows = [
            {
                'id': h.id,
                'asset_code': h.asset_id.code or '',
                'asset_name': h.asset_id.name or '',
                'event_type': h.event_type or '',
                'event_date': h.event_date.strftime('%Y-%m-%d %H:%M') if h.event_date else '',
                'old_state': h.old_state or '',
                'new_state': h.new_state or '',
                'employee': h.employee_id.name if h.employee_id else '',
                'user': h.user_id.name if h.user_id else '',
                'description': h.description or '',
            }
            for h in recent_history
        ]

        # ── Asset cards per state (max 50 per state to keep payload small) ────
        def _asset_card(a):
            active_asgn = a.assignment_ids.filtered(
                lambda r: r.is_active and not r.return_date
            )
            asgn = active_asgn[0] if active_asgn else None
            dep = (a.original_value or 0) - (a.value_residual or 0)
            dep_pct = round(dep / a.original_value * 100, 1) if a.original_value else 0
            return {
                'id': a.id,
                'code': a.code or '',
                'name': a.name or '',
                'serial': a.lot_id.name if a.lot_id else '',
                'category': a.model_id.name if a.model_id else '',
                'asset_state': a.asset_state,
                'employee': a.current_employee_id.name if a.current_employee_id else '',
                'purchase_value': a.original_value or 0,
                'net_book_value': a.value_residual or 0,
                'dep_pct': dep_pct,
                'registration_date': str(a.registration_date) if a.registration_date else '',
                'assign_date': str(asgn.assign_date) if asgn else '',
                'condition': asgn.condition_on_assign if asgn else '',
            }

        cards_by_state = {}
        for s in states:
            state_assets = assets.filtered(lambda a, _s=s: a.asset_state == _s)[:50]
            cards_by_state[s] = [_asset_card(a) for a in state_assets]

        return {
            'counts': counts,
            'total': len(assets),
            'total_value': total_value,
            'net_book_value': net_book_value,
            'total_depreciated': total_depreciated,
            'history': history_rows,
            'cards': cards_by_state,
            'currency': company.currency_id.symbol or '',
        }