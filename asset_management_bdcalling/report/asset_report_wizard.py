# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from collections import defaultdict
from datetime import datetime, time
import logging

_logger = logging.getLogger(__name__)


class AssetReportWizard(models.TransientModel):
    _name = 'asset.report.wizard'
    _description = 'Asset Report Wizard'

    # ─── Report Type ──────────────────────────────────────────────────────────

    report_type = fields.Selection(
        selection=[
            ('employee',     'Employee-wise Asset Report'),
            ('category',     'Category-wise Asset Summary'),
            ('depreciation', 'Depreciation Report'),
            ('movement',     'Asset Movement Report'),
            ('valuation',    'Asset Valuation Report'),
        ],
        string='Report Type',
        required=True,
        default='valuation',
    )

    # ─── Date Range ───────────────────────────────────────────────────────────

    date_from = fields.Date(
        string='Date From',
        default=lambda self: fields.Date.today().replace(month=1, day=1),
    )
    date_to = fields.Date(
        string='Date To',
        default=fields.Date.today,
    )

    # ─── Filters ──────────────────────────────────────────────────────────────

    employee_ids = fields.Many2many(
        'hr.employee',
        'asset_rpt_wiz_emp_rel',
        'wizard_id',
        'employee_id',
        string='Employees',
        help='Leave empty to include all employees.',
    )
    category_ids = fields.Many2many(
        'account.asset',
        'asset_rpt_wiz_cat_rel',
        'wizard_id',
        'category_id',
        string='Asset Categories',
        domain="[('state', '=', 'model')]",
        help='Leave empty to include all categories.',
    )
    asset_state_filter = fields.Selection(
        selection=[
            ('all',       'All Active'),
            ('available', 'Available'),
            ('assigned',  'Assigned'),
            ('scrapped',  'Scrapped'),
            ('disposed',  'Disposed'),
        ],
        string='Asset Status',
        default='all',
        required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # ─── Constraints ─────────────────────────────────────────────────────────

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError(_('Date From cannot be later than Date To.'))

    # ─── Private Helpers ─────────────────────────────────────────────────────

    def _get_asset_domain(self):
        """
        Base domain for registered AMS assets.
        Excludes: category templates (state='model'), unregistered drafts.
        """
        domain = [
            ('lot_id',      '!=', False),
            ('state',       '!=', 'model'),
            ('asset_state', 'not in', ['draft']),
            ('company_id',  '=',  self.company_id.id),
        ]
        if self.asset_state_filter != 'all':
            domain.append(('asset_state', '=', self.asset_state_filter))
        if self.category_ids:
            domain.append(('model_id', 'in', self.category_ids.ids))
        return domain

    def _get_assets(self):
        return self.env['account.asset'].sudo().search(
            self._get_asset_domain(),
            order='code asc',
        )

    @staticmethod
    def _fmt(amount):
        """Format a monetary amount to 2 d.p. with thousands separator."""
        return '{:,.2f}'.format(amount or 0.0)

    # ─── Data Methods (called directly from QWeb templates) ──────────────────

    def get_employee_report_data(self):
        """
        Returns a list of dicts — one per employee — containing their assigned
        assets plus an assignment map keyed by asset id.

        Layout:
            [{'employee': hr.employee|False, 'assets': [...], 'assign_map': {...},
              'count': int, 'total_value': float, 'total_nbv': float}, ...]

        Employees with no assets are omitted.  The last entry (employee=False)
        collects all un-assigned assets when asset_state_filter is 'all'.
        """
        assets = self._get_assets()
        if self.employee_ids:
            assets = assets.filtered(
                lambda a: a.current_employee_id in self.employee_ids
                or (not a.current_employee_id and self.asset_state_filter == 'all')
            )

        # Group by employee id (0 = unassigned)
        grouped = defaultdict(list)
        for asset in assets:
            key = asset.current_employee_id.id if asset.current_employee_id else 0
            grouped[key].append(asset)

        # Pre-fetch employee records to avoid N+1 queries
        employee_ids_needed = [k for k in grouped if k]
        emp_index = {
            e.id: e
            for e in self.env['hr.employee'].sudo().browse(employee_ids_needed)
        }

        result = []
        for emp_id, emp_assets in grouped.items():
            employee = emp_index.get(emp_id, False)

            # Build assignment map: asset.id → active asset.assignment or False
            assign_map = {}
            for a in emp_assets:
                active = a.assignment_ids.filtered(
                    lambda r: r.is_active and not r.return_date
                )
                assign_map[a.id] = active[0] if active else False

            result.append({
                'employee':    employee,
                'assets':      emp_assets,
                'assign_map':  assign_map,
                'count':       len(emp_assets),
                'total_value': sum(a.original_value for a in emp_assets),
                'total_nbv':   sum(a.value_residual  for a in emp_assets),
            })

        # Sort: named employees first (alpha), unassigned last
        result.sort(key=lambda x: (not x['employee'], x['employee'].name if x['employee'] else ''))
        return result

    def get_category_report_data(self):
        """
        Returns a list of dicts — one per asset category — with aggregated KPIs.

        Layout:
            [{'category': account.asset|False, 'assets': [...],
              'count': int, 'available': int, 'assigned': int, 'inactive': int,
              'total_value': float, 'total_nbv': float, 'total_dep': float}, ...]
        """
        assets = self._get_assets()

        grouped = defaultdict(list)
        for asset in assets:
            cat_id = asset.model_id.id if asset.model_id else 0
            grouped[cat_id].append(asset)

        cat_index = {
            c.id: c
            for c in self.env['account.asset'].sudo().browse(
                [k for k in grouped if k]
            )
        }

        result = []
        for cat_id, cat_assets in grouped.items():
            category   = cat_index.get(cat_id, False)
            total_orig = sum(a.original_value for a in cat_assets)
            total_nbv  = sum(a.value_residual  for a in cat_assets)
            result.append({
                'category':    category,
                'assets':      cat_assets,
                'count':       len(cat_assets),
                'available':   sum(1 for a in cat_assets if a.asset_state == 'available'),
                'assigned':    sum(1 for a in cat_assets if a.asset_state == 'assigned'),
                'inactive':    sum(1 for a in cat_assets if a.asset_state in ('scrapped', 'disposed')),
                'total_value': total_orig,
                'total_nbv':   total_nbv,
                'total_dep':   total_orig - total_nbv,
            })

        result.sort(key=lambda x: (not x['category'], x['category'].name if x['category'] else ''))
        return result

    def get_depreciation_report_data(self):
        """
        Per-asset depreciation summary.

        - ``moves``       — depreciation account.move records in [date_from, date_to]
        - ``period_dep``  — amount posted within the date range
        - ``cumulative_dep`` — total posted depreciation all-time
        - ``nbv``         — current net book value (native value_residual)

        Assets with no moves inside the date range are excluded when a range
        is provided (non-filtered → all assets with a depreciation board).
        """
        assets     = self._get_assets()
        date_from  = self.date_from
        date_to    = self.date_to

        result = []
        for asset in assets:
            all_moves = asset.depreciation_move_ids.sorted('date')

            # Period-filtered subset
            period_moves = all_moves
            if date_from:
                period_moves = period_moves.filtered(lambda m: m.date >= date_from)
            if date_to:
                period_moves = period_moves.filtered(lambda m: m.date <= date_to)

            # Skip assets with no moves in range when range is active
            if (date_from or date_to) and not period_moves:
                continue

            posted_all_time = all_moves.filtered(lambda m: m.state == 'posted')
            posted_period   = period_moves.filtered(lambda m: m.state == 'posted')
            pending_period  = period_moves.filtered(lambda m: m.state == 'draft')

            result.append({
                'asset':          asset,
                'period_moves':   period_moves,
                'posted_period':  posted_period,
                'pending_period': pending_period,
                'period_dep':     sum(posted_period.mapped('amount_total')),
                'cumulative_dep': sum(posted_all_time.mapped('amount_total')),
                'original_value': asset.original_value,
                'nbv':            asset.value_residual,
            })
        return result

    def get_movement_report_data(self):
        """
        Lifecycle events from asset.history filtered by date range.

        Optional additional filters: employee_ids, category_ids, asset_state.
        Returns an asset.history recordset sorted by event_date asc.
        """
        domain = [('company_id', '=', self.company_id.id)]

        if self.date_from:
            domain.append((
                'event_date', '>=',
                fields.Datetime.to_string(datetime.combine(self.date_from, time.min)),
            ))
        if self.date_to:
            domain.append((
                'event_date', '<=',
                fields.Datetime.to_string(datetime.combine(self.date_to, time.max)),
            ))
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        histories = self.env['asset.history'].sudo().search(
            domain,
            order='event_date asc',
        )

        # Post-filter: category and asset_state cannot be expressed in a single
        # domain without a join, so we filter the recordset in Python.
        if self.category_ids:
            histories = histories.filtered(
                lambda h: h.asset_id.model_id in self.category_ids
            )
        if self.asset_state_filter != 'all':
            histories = histories.filtered(
                lambda h: h.asset_id.asset_state == self.asset_state_filter
            )
        return histories

    def get_valuation_report_data(self):
        """
        Current valuation snapshot for all matching assets.

        Returns a dict with the asset recordset plus aggregated totals.
        """
        assets     = self._get_assets()
        total_orig = sum(assets.mapped('original_value'))
        total_nbv  = sum(assets.mapped('value_residual'))
        return {
            'assets':     assets,
            'total_orig': total_orig,
            'total_nbv':  total_nbv,
            'total_dep':  total_orig - total_nbv,
            'company':    self.company_id,
        }

    # ─── Print Dispatcher ────────────────────────────────────────────────────

    _REPORT_XML_IDS = {
        'employee':     'asset_management_bdcalling.action_report_employee_asset',
        'category':     'asset_management_bdcalling.action_report_category_summary',
        'depreciation': 'asset_management_bdcalling.action_report_depreciation_schedule',
        'movement':     'asset_management_bdcalling.action_report_asset_movement',
        'valuation':    'asset_management_bdcalling.action_report_asset_valuation_full',
    }

    def action_print_report(self):
        self.ensure_one()
        xml_id = self._REPORT_XML_IDS.get(self.report_type)
        if not xml_id:
            raise UserError(_('Unknown report type: %s') % self.report_type)
        return self.env.ref(xml_id).report_action(self)