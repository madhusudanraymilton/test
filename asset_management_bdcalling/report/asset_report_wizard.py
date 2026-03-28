# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
# from odoo.exceptions import UserError
# from collections import defaultdict
# from datetime import datetime, time
# import logging

# _logger = logging.getLogger(__name__)


# class AssetReportWizard(models.TransientModel):
#     _name = 'asset.report.wizard'
#     _description = 'Asset Report Wizard'

#     # ─── Report Type ──────────────────────────────────────────────────────────

#     report_type = fields.Selection(
#         selection=[
#             ('employee',     'Employee-wise Asset Report'),
#             ('category',     'Category-wise Asset Summary'),
#             ('depreciation', 'Depreciation Report'),
#             ('movement',     'Asset Movement Report'),
#             ('valuation',    'Asset Valuation Report'),
#         ],
#         string='Report Type',
#         required=True,
#         default='valuation',
#     )

#     # ─── Date Range ───────────────────────────────────────────────────────────

#     date_from = fields.Date(
#         string='Date From',
#         default=lambda self: fields.Date.today().replace(month=1, day=1),
#     )
#     date_to = fields.Date(
#         string='Date To',
#         default=fields.Date.today,
#     )

#     # ─── Filters ──────────────────────────────────────────────────────────────

#     employee_ids = fields.Many2many(
#         'hr.employee',
#         'asset_rpt_wiz_emp_rel',
#         'wizard_id',
#         'employee_id',
#         string='Employees',
#         help='Leave empty to include all employees.',
#     )

#     category_ids = fields.Many2many(
#         'account.asset',
#         'asset_rpt_wiz_cat_rel',
#         'wizard_id',
#         'category_id',
#         string='Asset Categories',
#         domain="[('state', '=', 'model')]",
#         help='Leave empty to include all categories.',
#     )

#     product_ids = fields.Many2many(
#         'product.product',
#         'asset_rpt_wiz_prod_rel',
#         'wizard_id',
#         'product_id',
#         string='Products',
#         domain="[('is_asset', 'in', [True])]",
#         help='Leave empty to include all products.',
#     )

#     lot_ids = fields.Many2many(
#         'stock.lot',
#         'asset_rpt_wiz_lot_rel',
#         'wizard_id',
#         'lot_id',
#         string='Serial Numbers',
#         help='Leave empty to include all serial numbers.',
#     )

#     asset_state_filter = fields.Selection(
#         selection=[
#             ('all',       'All Active'),
#             ('available', 'Available'),
#             ('assigned',  'Assigned'),
#             ('scrapped',  'Scrapped'),
#             ('disposed',  'Disposed'),
#         ],
#         string='Asset Status',
#         default='all',
#         required=True,
#     )

#     company_id = fields.Many2one(
#         'res.company',
#         string='Company',
#         required=True,
#         default=lambda self: self.env.company,
#     )

#     # ─── Constraints ─────────────────────────────────────────────────────────

#     @api.constrains('date_from', 'date_to')
#     def _check_dates(self):
#         for rec in self:
#             if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
#                 raise UserError(_('Date From cannot be later than Date To.'))

#     # ─── Private Helpers ─────────────────────────────────────────────────────

#     def _get_asset_domain(self):
#         """
#         Base domain for registered AMS assets.
#         Excludes: category templates (state='model'), unregistered drafts.
#         """
#         domain = [
#             ('lot_id',      '!=', False),
#             ('state',       '!=', 'model'),
#             ('asset_state', 'not in', ['draft']),
#             ('company_id',  '=',  self.company_id.id),
#         ]
#         if self.asset_state_filter != 'all':
#             domain.append(('asset_state', '=', self.asset_state_filter))
#         if self.category_ids:
#             domain.append(('model_id', 'in', self.category_ids.ids))
#         return domain

#     def _get_assets(self):
#         return self.env['account.asset'].sudo().search(
#             self._get_asset_domain(),
#             order='code asc',
#         )

#     @staticmethod
#     def _fmt(amount):
#         """Format a monetary amount to 2 d.p. with thousands separator."""
#         return '{:,.2f}'.format(amount or 0.0)

#     # ─── Data Methods (called directly from QWeb templates) ──────────────────

#     def get_employee_report_data(self):
#         assets = self._get_assets()
#         if self.employee_ids:
#             assets = assets.filtered(
#                 lambda a: a.current_employee_id in self.employee_ids
#             )
#         else:
#             # ── CHANGE: exclude unassigned assets entirely ──────────────────
#             assets = assets.filtered(lambda a: a.current_employee_id)

#         # Group by employee id
#         grouped = defaultdict(list)
#         for asset in assets:
#             key = asset.current_employee_id.id
#             grouped[key].append(asset)

#         employee_ids_needed = list(grouped.keys())
#         emp_index = {
#             e.id: e
#             for e in self.env['hr.employee'].sudo().browse(employee_ids_needed)
#         }

#         result = []
#         for emp_id, emp_assets in grouped.items():
#             employee = emp_index.get(emp_id)
#             if not employee:          # belt-and-suspenders: skip if somehow False
#                 continue

#             assign_map = {}
#             for a in emp_assets:
#                 active = a.assignment_ids.filtered(
#                     lambda r: r.is_active and not r.return_date
#                 )
#                 assign_map[a.id] = active[0] if active else False

#             result.append({
#                 'employee':    employee,
#                 'assets':      emp_assets,
#                 'assign_map':  assign_map,
#                 'count':       len(emp_assets),
#                 'total_value': sum(a.original_value for a in emp_assets),
#                 'total_nbv':   sum(a.value_residual  for a in emp_assets),
#             })

#         result.sort(key=lambda x: x['employee'].name)
#         return result

#     def get_category_report_data(self):
#         """
#         Returns a list of dicts — one per asset category — with aggregated KPIs.

#         Layout:
#             [{'category': account.asset|False, 'assets': [...],
#               'count': int, 'available': int, 'assigned': int, 'inactive': int,
#               'total_value': float, 'total_nbv': float, 'total_dep': float}, ...]
#         """
#         assets = self._get_assets()

#         grouped = defaultdict(list)
#         for asset in assets:
#             cat_id = asset.model_id.id if asset.model_id else 0
#             grouped[cat_id].append(asset)

#         cat_index = {
#             c.id: c
#             for c in self.env['account.asset'].sudo().browse(
#                 [k for k in grouped if k]
#             )
#         }

#         result = []
#         for cat_id, cat_assets in grouped.items():
#             category   = cat_index.get(cat_id, False)
#             total_orig = sum(a.original_value for a in cat_assets)
#             total_nbv  = sum(a.value_residual  for a in cat_assets)
#             result.append({
#                 'category':    category,
#                 'assets':      cat_assets,
#                 'count':       len(cat_assets),
#                 'available':   sum(1 for a in cat_assets if a.asset_state == 'available'),
#                 'assigned':    sum(1 for a in cat_assets if a.asset_state == 'assigned'),
#                 'inactive':    sum(1 for a in cat_assets if a.asset_state in ('scrapped', 'disposed')),
#                 'total_value': total_orig,
#                 'total_nbv':   total_nbv,
#                 'total_dep':   total_orig - total_nbv,
#             })

#         result.sort(key=lambda x: (not x['category'], x['category'].name if x['category'] else ''))
#         return result

#     def get_depreciation_report_data(self):
#         """
#         Per-asset depreciation summary.

#         - ``moves``       — depreciation account.move records in [date_from, date_to]
#         - ``period_dep``  — amount posted within the date range
#         - ``cumulative_dep`` — total posted depreciation all-time
#         - ``nbv``         — current net book value (native value_residual)

#         Assets with no moves inside the date range are excluded when a range
#         is provided (non-filtered → all assets with a depreciation board).
#         """
#         assets     = self._get_assets()
#         date_from  = self.date_from
#         date_to    = self.date_to

#         result = []
#         for asset in assets:
#             all_moves = asset.depreciation_move_ids.sorted('date')

#             # Period-filtered subset
#             period_moves = all_moves
#             if date_from:
#                 period_moves = period_moves.filtered(lambda m: m.date >= date_from)
#             if date_to:
#                 period_moves = period_moves.filtered(lambda m: m.date <= date_to)

#             # Skip assets with no moves in range when range is active
#             if (date_from or date_to) and not period_moves:
#                 continue

#             posted_all_time = all_moves.filtered(lambda m: m.state == 'posted')
#             posted_period   = period_moves.filtered(lambda m: m.state == 'posted')
#             pending_period  = period_moves.filtered(lambda m: m.state == 'draft')

#             result.append({
#                 'asset':          asset,
#                 'period_moves':   period_moves,
#                 'posted_period':  posted_period,
#                 'pending_period': pending_period,
#                 'period_dep':     sum(posted_period.mapped('amount_total')),
#                 'cumulative_dep': sum(posted_all_time.mapped('amount_total')),
#                 'original_value': asset.original_value,
#                 'nbv':            asset.value_residual,
#             })
#         return result

#     # def get_movement_report_data(self):
#     #     """
#     #     Lifecycle events from asset.history filtered by date range.

#     #     Optional additional filters: employee_ids, category_ids, asset_state.
#     #     Returns an asset.history recordset sorted by event_date asc.
#     #     """
#     #     domain = [('company_id', '=', self.company_id.id)]

#     #     if self.date_from:
#     #         domain.append((
#     #             'event_date', '>=',
#     #             fields.Datetime.to_string(datetime.combine(self.date_from, time.min)),
#     #         ))
#     #     if self.date_to:
#     #         domain.append((
#     #             'event_date', '<=',
#     #             fields.Datetime.to_string(datetime.combine(self.date_to, time.max)),
#     #         ))
#     #     if self.employee_ids:
#     #         domain.append(('employee_id', 'in', self.employee_ids.ids))

#     #     histories = self.env['asset.history'].sudo().search(
#     #         domain,
#     #         order='event_date asc',
#     #     )

#     #     # Post-filter: category and asset_state cannot be expressed in a single
#     #     # domain without a join, so we filter the recordset in Python.
#     #     if self.category_ids:
#     #         histories = histories.filtered(
#     #             lambda h: h.asset_id.model_id in self.category_ids
#     #         )
#     #     if self.asset_state_filter != 'all':
#     #         histories = histories.filtered(
#     #             lambda h: h.asset_id.asset_state == self.asset_state_filter
#     #         )
#     #     return histories
#     def get_movement_report_data(self):
#         """
#         Lifecycle events from asset.history filtered by date range,
#         employee, category, asset_state, product, and serial number.
#         """
#         domain = [('company_id', '=', self.company_id.id)]

#         if self.date_from:
#             domain.append((
#                 'event_date', '>=',
#                 fields.Datetime.to_string(
#                     datetime.combine(self.date_from, time.min)
#                 ),
#             ))
#         if self.date_to:
#             domain.append((
#                 'event_date', '<=',
#                 fields.Datetime.to_string(
#                     datetime.combine(self.date_to, time.max)
#                 ),
#             ))
#         if self.employee_ids:
#             domain.append(('employee_id', 'in', self.employee_ids.ids))

#         # Product and serial filters can be pushed into the domain directly
#         # because asset.history → asset_id → product_id / lot_id are stored
#         # on account.asset (a real table) — ORM resolves the join.
#         if self.product_ids:
#             domain.append(('asset_id.product_id', 'in', self.product_ids.ids))
#         if self.lot_ids:
#             domain.append(('asset_id.lot_id', 'in', self.lot_ids.ids))

#         histories = self.env['asset.history'].sudo().search(
#             domain,
#             order='event_date asc',
#         )

#         # Python-level post-filters (no clean join path in domain)
#         if self.category_ids:
#             histories = histories.filtered(
#                 lambda h: h.asset_id.model_id in self.category_ids
#             )
#         if self.asset_state_filter != 'all':
#             histories = histories.filtered(
#                 lambda h: h.asset_id.asset_state == self.asset_state_filter
#             )
#         return histories

#     def get_valuation_report_data(self):
#         """
#         Current valuation snapshot for all matching assets.

#         Returns a dict with the asset recordset plus aggregated totals.
#         """
#         assets     = self._get_assets()
#         total_orig = sum(assets.mapped('original_value'))
#         total_nbv  = sum(assets.mapped('value_residual'))
#         return {
#             'assets':     assets,
#             'total_orig': total_orig,
#             'total_nbv':  total_nbv,
#             'total_dep':  total_orig - total_nbv,
#             'company':    self.company_id,
#         }

#     # ─── Print Dispatcher ────────────────────────────────────────────────────

#     _REPORT_XML_IDS = {
#         'employee':     'asset_management_bdcalling.action_report_employee_asset',
#         'category':     'asset_management_bdcalling.action_report_category_summary',
#         'depreciation': 'asset_management_bdcalling.action_report_depreciation_schedule',
#         'movement':     'asset_management_bdcalling.action_report_asset_movement',
#         'valuation':    'asset_management_bdcalling.action_report_asset_valuation_full',
#     }

#     def action_print_report(self):
#         self.ensure_one()
#         xml_id = self._REPORT_XML_IDS.get(self.report_type)
#         if not xml_id:
#             raise UserError(_('Unknown report type: %s') % self.report_type)
#         return self.env.ref(xml_id).report_action(self)

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

    # ─── Common Filters ───────────────────────────────────────────────────────

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

    # ─── Movement Report Filters ──────────────────────────────────────────────

    # ── Computed domain helpers (non-stored, drive cascading domains) ─────────

    available_product_ids = fields.Many2many(
        'product.product',
        string='Available Asset Names',
        compute='_compute_movement_filter_domains',
    )
    available_lot_domain_ids = fields.Many2many(
        'stock.lot',
        string='Available Serial Numbers',
        compute='_compute_movement_filter_domains',
    )

    # ── Actual user-facing filter fields ──────────────────────────────────────

    product_ids = fields.Many2many(
        'product.product',
        'asset_rpt_wiz_prod_rel',
        'wizard_id',
        'product_id',
        string='Asset Name',
        domain="[('id', 'in', available_product_ids)]",
        help='Filtered by the selected categories. Leave empty for all.',
    )
    lot_ids = fields.Many2many(
        'stock.lot',
        'asset_rpt_wiz_lot_rel',
        'wizard_id',
        'lot_id',
        string='Serial Number',
        domain="[('id', 'in', available_lot_domain_ids)]",
        help='Filtered by the selected categories and asset names. Leave empty for all.',
    )

    # ─── Cascading Compute ────────────────────────────────────────────────────

    # @api.depends('category_ids', 'product_ids', 'company_id', 'asset_state_filter')
    # def _compute_movement_filter_domains(self):
    #     """
    #     Recomputes which product.product and stock.lot records are valid
    #     choices given the currently selected categories / products.

    #     Both helpers are derived from account.asset records that:
    #       - are registered AMS assets (lot_id set, state != 'model')
    #       - belong to the wizard's company
    #       - match the selected category/product (when not empty)
    #       - match the selected asset_state_filter (when not 'all')

    #     The results drive the domain= attributes on product_ids and lot_ids,
    #     so the dropdowns only show records that actually correspond to an asset.
    #     """
    #     for rec in self:
    #         # ── Base domain shared by both helpers ────────────────────────────
    #         base = [
    #             ('lot_id',      '!=', False),
    #             ('state',       '!=', 'model'),
    #             ('asset_state', 'not in', ['draft']),
    #             ('company_id',  '=', rec.company_id.id),
    #         ]
    #         if rec.asset_state_filter != 'all':
    #             base.append(('asset_state', '=', rec.asset_state_filter))

    #         # ── Available products: filter by category only ───────────────────
    #         prod_domain = list(base)
    #         if rec.category_ids:
    #             prod_domain.append(('model_id', 'in', rec.category_ids.ids))
    #         prod_assets = self.env['account.asset'].sudo().search(prod_domain)
    #         rec.available_product_ids = prod_assets.mapped('product_id')

    #         # ── Available lots: filter by category AND product ────────────────
    #         lot_domain = list(base)
    #         if rec.category_ids:
    #             lot_domain.append(('model_id', 'in', rec.category_ids.ids))
    #         if rec.product_ids:
    #             lot_domain.append(('product_id', 'in', rec.product_ids.ids))
    #         lot_assets = self.env['account.asset'].sudo().search(lot_domain)
    #         rec.available_lot_domain_ids = lot_assets.mapped('lot_id')
    @api.depends('category_ids', 'product_ids', 'company_id')
    def _compute_movement_filter_domains(self):
        """
        Dropdown lists show every asset registered in any lifecycle state:
        available, assigned, scrapped, disposed.
        Draft (never registered) assets are excluded.
        """
        for rec in self:
            base = [
                ('lot_id',      '!=', False),
                ('state',       '!=', 'model'),
                ('asset_state', 'in', ['available', 'assigned', 'scrapped', 'disposed']),
                ('company_id',  '=',  rec.company_id.id),
            ]

            # Asset Name dropdown — narrowed by category only
            prod_domain = list(base)
            if rec.category_ids:
                prod_domain.append(('model_id', 'in', rec.category_ids.ids))
            prod_assets = self.env['account.asset'].sudo().search(prod_domain)
            rec.available_product_ids = prod_assets.mapped('product_id')

            # Serial Number dropdown — narrowed by category + asset name
            lot_domain = list(base)
            if rec.category_ids:
                lot_domain.append(('model_id', 'in', rec.category_ids.ids))
            if rec.product_ids:
                lot_domain.append(('product_id', 'in', rec.product_ids.ids))
            lot_assets = self.env['account.asset'].sudo().search(lot_domain)
            rec.available_lot_domain_ids = lot_assets.mapped('lot_id')

    # ─── Onchange: cascade-clear child selections when parent changes ─────────

    # @api.onchange('category_ids')
    # def _onchange_category_ids(self):
    #     """
    #     When category selection changes, remove any product_ids that no longer
    #     belong to the new category set, and clear lot_ids entirely.
    #     """
    #     if self.product_ids and self.category_ids:
    #         # Recompute inline so available_product_ids is fresh
    #         prod_domain = [
    #             ('lot_id',      '!=', False),
    #             ('state',       '!=', 'model'),
    #             ('asset_state', 'not in', ['draft']),
    #             ('company_id',  '=', self.company_id.id),
    #             ('model_id',    'in', self.category_ids.ids),
    #         ]
    #         valid_products = (
    #             self.env['account.asset'].sudo()
    #             .search(prod_domain)
    #             .mapped('product_id')
    #         )
    #         self.product_ids = self.product_ids & valid_products
    #     self.lot_ids = [(5, 0, 0)]
    @api.onchange('category_ids')
    def _onchange_category_ids(self):
        if self.product_ids and self.category_ids:
            prod_domain = [
                ('lot_id',      '!=', False),
                ('state',       '!=', 'model'),
                ('asset_state', 'in', ['available', 'assigned', 'scrapped', 'disposed']),
                ('company_id',  '=',  self.company_id.id),
                ('model_id',    'in', self.category_ids.ids),
            ]
            valid_products = (
                self.env['account.asset'].sudo()
                .search(prod_domain)
                .mapped('product_id')
            )
            self.product_ids = self.product_ids & valid_products
        self.lot_ids = [(5, 0, 0)]

    # @api.onchange('product_ids')
    # def _onchange_product_ids(self):
    #     """
    #     When product (asset name) selection changes, remove lot_ids that no
    #     longer belong to the new product set.
    #     """
    #     if self.lot_ids and self.product_ids:
    #         lot_domain = [
    #             ('lot_id',      '!=', False),
    #             ('state',       '!=', 'model'),
    #             ('asset_state', 'not in', ['draft']),
    #             ('company_id',  '=', self.company_id.id),
    #             ('product_id',  'in', self.product_ids.ids),
    #         ]
    #         if self.category_ids:
    #             lot_domain.append(('model_id', 'in', self.category_ids.ids))
    #         valid_lots = (
    #             self.env['account.asset'].sudo()
    #             .search(lot_domain)
    #             .mapped('lot_id')
    #         )
    #         self.lot_ids = self.lot_ids & valid_lots
    #     elif not self.product_ids:
    #         self.lot_ids = [(5, 0, 0)]
    @api.onchange('product_ids')
    def _onchange_product_ids(self):
        if self.lot_ids and self.product_ids:
            lot_domain = [
                ('lot_id',      '!=', False),
                ('state',       '!=', 'model'),
                ('asset_state', 'in', ['available', 'assigned', 'scrapped', 'disposed']),
                ('company_id',  '=',  self.company_id.id),
                ('product_id',  'in', self.product_ids.ids),
            ]
            if self.category_ids:
                lot_domain.append(('model_id', 'in', self.category_ids.ids))
            valid_lots = (
                self.env['account.asset'].sudo()
                .search(lot_domain)
                .mapped('lot_id')
            )
            self.lot_ids = self.lot_ids & valid_lots
        elif not self.product_ids:
            self.lot_ids = [(5, 0, 0)]

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
        return '{:,.2f}'.format(amount or 0.0)

    # ─── Data Methods ─────────────────────────────────────────────────────────

    def get_employee_report_data(self):
        assets = self._get_assets()
        if self.employee_ids:
            assets = assets.filtered(
                lambda a: a.current_employee_id in self.employee_ids
            )
        else:
            assets = assets.filtered(lambda a: a.current_employee_id)

        grouped = defaultdict(list)
        for asset in assets:
            key = asset.current_employee_id.id
            grouped[key].append(asset)

        emp_index = {
            e.id: e
            for e in self.env['hr.employee'].sudo().browse(list(grouped.keys()))
        }

        result = []
        for emp_id, emp_assets in grouped.items():
            employee = emp_index.get(emp_id)
            if not employee:
                continue
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

        result.sort(key=lambda x: x['employee'].name)
        return result

    def get_category_report_data(self):
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
                'category':  category,
                'assets':    cat_assets,
                'count':     len(cat_assets),
                'available': sum(1 for a in cat_assets if a.asset_state == 'available'),
                'assigned':  sum(1 for a in cat_assets if a.asset_state == 'assigned'),
                'inactive':  sum(1 for a in cat_assets if a.asset_state in ('scrapped', 'disposed')),
                'total_value': total_orig,
                'total_nbv':   total_nbv,
                'total_dep':   total_orig - total_nbv,
            })

        result.sort(key=lambda x: (not x['category'], x['category'].name if x['category'] else ''))
        return result

    def get_depreciation_report_data(self):
        assets    = self._get_assets()
        date_from = self.date_from
        date_to   = self.date_to

        result = []
        for asset in assets:
            all_moves = asset.depreciation_move_ids.sorted('date')

            period_moves = all_moves
            if date_from:
                period_moves = period_moves.filtered(lambda m: m.date >= date_from)
            if date_to:
                period_moves = period_moves.filtered(lambda m: m.date <= date_to)

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
        Lifecycle events from asset.history filtered by date range,
        employee, category, asset_state, asset name (product), and serial
        number (lot). Category/product/lot form a cascading chain — each
        narrows the result set of the next.
        """
        domain = [('company_id', '=', self.company_id.id)]

        if self.date_from:
            domain.append((
                'event_date', '>=',
                fields.Datetime.to_string(
                    datetime.combine(self.date_from, time.min)
                ),
            ))
        if self.date_to:
            domain.append((
                'event_date', '<=',
                fields.Datetime.to_string(
                    datetime.combine(self.date_to, time.max)
                ),
            ))
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        # Push product and lot into the ORM domain — the ORM resolves the
        # join through asset_id on account.asset (a real table column).
        if self.product_ids:
            domain.append(('asset_id.product_id', 'in', self.product_ids.ids))
        if self.lot_ids:
            domain.append(('asset_id.lot_id', 'in', self.lot_ids.ids))

        histories = self.env['asset.history'].sudo().search(
            domain,
            order='event_date asc',
        )

        # Python post-filters (no clean single-domain join for these)
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