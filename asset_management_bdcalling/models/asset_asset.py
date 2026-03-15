# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AssetAsset(models.Model):
    _name = 'asset.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code'

    # ─── Identity ────────────────────────────────────────────────────────────

    name = fields.Char(
        string='Asset Name',
        compute='_compute_name',
        store=True,
        readonly=False,
    )
    code = fields.Char(
        string='Asset Code',
        readonly=True,
        copy=False,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    active = fields.Boolean(string='Active', default=True)

    # ─── Product & Serial ────────────────────────────────────────────────────

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True,
        domain="[('is_asset', 'in', [True])]",
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number (Lot)',
        required=True,
        tracking=True,
        domain="[('id', 'in', available_lot_ids)]",
    )

    available_lot_ids = fields.Many2many(
        'stock.lot',
        string='Available Serials',
        compute='_compute_available_lot_ids',
        readonly=True,
    )
    
    serial_number = fields.Char(
        string='Serial Number',
        related='lot_id.name',
        store=True,
        readonly=True,
        index=True,
    )

    odoo_asset_id = fields.Many2one(
        'account.asset', string='Accounting Asset',
        readonly=True, ondelete='set null', copy=False, index=True,
    )

    # ADD this ↓
    depreciation_move_ids = fields.One2many(
        related='odoo_asset_id.depreciation_move_ids',
        string='Depreciation Entries',
        readonly=True,
    )

    # ─── Classification ──────────────────────────────────────────────────────

    category_id = fields.Many2one(
        'account.asset',
        string='Asset Category',
        required=True,
        domain="[('company_id', '=', company_id), ('state', '=', 'model')]",
    )

    # ─── State ───────────────────────────────────────────────────────────────

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('available', 'Available'),
            ('assigned', 'Assigned'),
            ('returned', 'Returned'),
            ('scrapped', 'Scrapped'),
            ('disposed', 'Disposed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )

    # ─── Dates & Financials ──────────────────────────────────────────────────

    purchase_date = fields.Date(string='Purchase Date', tracking=True)
    registration_date = fields.Date(string='Registration Date', readonly=True)
    purchase_price = fields.Monetary(
        string='Purchase Price',
        currency_field='currency_id',
        required=True,
        tracking=True,
        groups='account.group_account_manager,custom_asset_management.group_asset_manager',
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    residual_value = fields.Monetary(
        string='Net Book Value',
        currency_field='currency_id',
        compute='_compute_residual_value',
        store=True,
        groups='account.group_account_manager,custom_asset_management.group_asset_manager',
    )

    # ─── Location & Assignment ───────────────────────────────────────────────

    location_id = fields.Many2one(
        'stock.location',
        string='Asset Location',
    )

    current_employee_id = fields.Many2one(
        'hr.employee',
        string='Assigned To',
        tracking=True,
        domain="[('company_id', '=', company_id)]",
    )

    # ─── Relational Lines ────────────────────────────────────────────────────

    depreciation_line_ids = fields.One2many(
        'asset.depreciation.line',
        'asset_id',
        string='Depreciation Schedule',
    )

    assignment_ids = fields.One2many(
        'asset.assignment',
        'asset_id',
        string='Assignment History',
    )

    history_ids = fields.One2many(
        'asset.history',
        'asset_id',
        string='Lifecycle History',
    )

    # total_assets = fields.Integer(
    #     string='Total Assets',
    #     compute='_compute_total_assets',
    # )

    notes = fields.Text(string='Notes')

    # ─── SQL Constraints ─────────────────────────────────────────────────────

    _sql_constraints = [
        (
            'lot_unique',
            'UNIQUE(lot_id)',
            'A serial number can only be registered as one asset.',
        ),
        (
            'serial_company_unique',
            'UNIQUE(serial_number, company_id)',
            'Serial number must be unique per company.',
        ),
        (
            'code_unique',
            'UNIQUE(code)',
            'Asset code must be globally unique.',
        ),
    ]

    # ─── Compute Methods ─────────────────────────────────────────────────────
    @api.depends('product_id', 'lot_id')
    def _compute_name(self):
        for rec in self:
            if rec.product_id and rec.lot_id:
                rec.name = f'{rec.product_id.name} [{rec.lot_id.name}]'
            elif rec.product_id:
                rec.name = rec.product_id.name
            else:
                rec.name = rec.name or _('New Asset')

    # @api.depends('purchase_price', 'depreciation_line_ids.amount',
    #              'depreciation_line_ids.move_posted_check')
    # def _compute_residual_value(self):
    #     for rec in self:
    #         posted_total = sum(
    #             line.amount
    #             for line in rec.depreciation_line_ids
    #             if line.move_posted_check
    #         )
    #         rec.residual_value = rec.purchase_price - posted_total

    @api.depends('odoo_asset_id', 'odoo_asset_id.value_residual', 'purchase_price')
    def _compute_residual_value(self):
        for rec in self:
            rec.residual_value = (
                rec.odoo_asset_id.value_residual
                if rec.odoo_asset_id
                else rec.purchase_price - sum(
                    l.amount for l in rec.depreciation_line_ids if l.move_posted_check
                )
            )
    
    # ─── ORM Overrides ───────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('asset.asset.code') or '/'
        return super().create(vals_list)

    # ─── Action Buttons ──────────────────────────────────────────────────────
    def action_view_accounting_asset(self):
        self.ensure_one()
        if not self.odoo_asset_id:
            raise UserError(_('No accounting asset linked. Register first.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'res_id': self.odoo_asset_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_register(self):
        """Open the register wizard to move serial from inventory → asset location."""
        self.ensure_one()
        self.state = 'available'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Asset'),
            'res_model': 'asset.register.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_lot_id': self.lot_id.id,
                'default_category_id': self.category_id.id,
                'default_purchase_price': self.purchase_price,
            },
        }

    def action_unregister(self):
        """Open the unregister wizard."""
        self.ensure_one()
        if self.state != 'available':
            raise UserError(_('Only assets in "Available" state can be unregistered.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Unregister Asset'),
            'res_model': 'asset.unregister.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id},
        }

    def action_assign(self):
        """Open the assign wizard."""
        self.ensure_one()
        if self.state != 'available':
            raise UserError(_('Only assets in "Available" state can be assigned.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Asset'),
            'res_model': 'asset.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id},
        }

    def action_return(self):
        """Open the return wizard."""
        self.ensure_one()
        if self.state != 'assigned':
            raise UserError(_('Only assigned assets can be returned.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Asset'),
            'res_model': 'asset.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id},
        }

    def action_scrap(self):
        """Scrap the asset — available or assigned."""
        self.ensure_one()
        if self.state not in ('available', 'assigned'):
            raise UserError(_('Only available or assigned assets can be scrapped.'))
        old_state = self.state
        self.write({'state': 'scrapped', 'current_employee_id': False})
        self._log_history(
            event_type='scrap',
            old_state=old_state,
            new_state='scrapped',
            description=_('Asset scrapped by %s') % self.env.user.name,
        )
        return True

    def action_dispose(self):
        """Dispose the asset — available or assigned."""
        self.ensure_one()
        if self.state not in ('available', 'assigned'):
            raise UserError(_('Only available or assigned assets can be disposed.'))
        old_state = self.state
        self.write({'state': 'disposed', 'current_employee_id': False})
        self._log_history(
            event_type='dispose',
            old_state=old_state,
            new_state='disposed',
            description=_('Asset disposed by %s') % self.env.user.name,
        )
        return True

    # ─── History Logging ─────────────────────────────────────────────────────

    def _log_history(self, event_type, old_state=None, new_state=None,
                     employee_id=None, description=None, metadata=None):
        """Append an immutable history record for every state transition."""
        self.env['asset.history'].sudo().create({
            'asset_id': self.id,
            'event_type': event_type,
            'event_date': fields.Datetime.now(),
            'old_state': old_state or self._origin.state,
            'new_state': new_state or self.state,
            'employee_id': employee_id,
            'user_id': self.env.uid,
            'description': description or _(
                'State changed: %s → %s'
            ) % (old_state, new_state),
            'metadata': metadata or {},
            'company_id': self.company_id.id,
        })

    # ─── available lot ids ───────────────────────────────────────────────
    @api.depends('product_id')
    def _compute_available_lot_ids(self):
        """
        Returns lots that are NOT currently locked by a non-draft asset.
        A lot is considered free when:
          - no asset references it, OR
          - the only referencing asset is this record itself (edit mode), OR
          - the referencing asset is in state 'draft' (unregistered).
        """
        # Lots locked by active assets (excluding this record)
        locked_lots = self.env['asset.asset'].search([
            ('lot_id', '!=', False),
            ('state', '!=', 'draft'),
            ('id', 'not in', self.ids),
        ]).mapped('lot_id')

        for rec in self:
            domain = [('product_id', '=', rec.product_id.id)] if rec.product_id else []
            product_lots = self.env['stock.lot'].search(domain)
            rec.available_lot_ids = product_lots - locked_lots

    # ─── Depreciation Board ──────────────────────────────────────────────────

    # def _generate_depreciation_board(self):
    #     """Generate the full depreciation schedule on registration."""
    #     self.ensure_one()
    #     # Remove any existing unposted lines
    #     self.depreciation_line_ids.filtered(lambda l: not l.move_posted_check).unlink()

    #     category = self.category_id
    #     if category.depreciation_method == 'straight_line':
    #         lines = self._compute_straight_line()
    #     else:
    #         lines = self._compute_declining_balance()

    #     for line_vals in lines:
    #         line_vals.update({
    #             'asset_id': self.id,
    #             'company_id': self.company_id.id,
    #             'currency_id': self.currency_id.id,
    #         })
    #     self.env['asset.depreciation.line'].create(lines)

    # def _compute_straight_line(self):
    #     """Straight-line depreciation schedule."""
    #     self.ensure_one()
    #     category = self.category_id
    #     depreciable_amount = self.purchase_price * (
    #         1 - category.non_depreciable_pct / 100.0
    #     )
    #     monthly_amount = depreciable_amount / category.duration_months
    #     lines = []
    #     remaining = self.purchase_price
    #     cumulative = 0.0
    #     start_date = self.registration_date or fields.Date.today()

    #     for i in range(category.duration_months):
    #         dep_date = start_date + relativedelta(months=i + 1)
    #         # Last line absorbs rounding
    #         if i == category.duration_months - 1:
    #             amount = depreciable_amount - cumulative
    #         else:
    #             amount = round(monthly_amount, self.currency_id.decimal_places)
    #         cumulative += amount
    #         remaining -= amount
    #         lines.append({
    #             'sequence': i + 1,
    #             'depreciation_date': dep_date,
    #             'amount': amount,
    #             'remaining_value': max(remaining, 0.0),
    #             'depreciated_value': cumulative,
    #             'move_check': False,
    #             'move_posted_check': False,
    #         })
    #     return lines

    # def _compute_declining_balance(self):
    #     """Declining balance depreciation schedule."""
    #     self.ensure_one()
    #     category = self.category_id
    #     duration_years = category.duration_months / 12.0
    #     residual_pct = category.non_depreciable_pct / 100.0

    #     if residual_pct > 0 and residual_pct < 1:
    #         rate = 1 - (residual_pct ** (1.0 / duration_years))
    #     else:
    #         rate = (1.0 / duration_years) * 2  # double-declining fallback

    #     book_value = self.purchase_price
    #     lines = []
    #     start_date = self.registration_date or fields.Date.today()
    #     decimal_places = self.currency_id.decimal_places

    #     for i in range(category.duration_months):
    #         dep_date = start_date + relativedelta(months=i + 1)
    #         monthly_dep = round(book_value * rate / 12.0, decimal_places)
    #         # Clamp to non-negative book value
    #         monthly_dep = min(monthly_dep, book_value)
    #         book_value -= monthly_dep
    #         lines.append({
    #             'sequence': i + 1,
    #             'depreciation_date': dep_date,
    #             'amount': monthly_dep,
    #             'remaining_value': max(book_value, 0.0),
    #             'depreciated_value': self.purchase_price - book_value,
    #             'move_check': False,
    #             'move_posted_check': False,
    #         })
    #     return lines

    # ─── Dashboard Data ──────────────────────────────────────────────────────

    @api.model
    def _cron_check_archived_employee_assets(self):
        """
        Daily cron: find assets still assigned to archived employees and
        create a return activity on each, notifying the Asset Manager.
        """
        archived_employees = self.env['hr.employee'].with_context(active_test=False).search([
            ('active', '=', False),
        ])
        if not archived_employees:
            return

        assets = self.search([
            ('current_employee_id', 'in', archived_employees.ids),
            ('state', '=', 'assigned'),
        ])

        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for asset in assets:
            _logger.warning(
                'AMS: Asset %s is still assigned to archived employee %s',
                asset.code,
                asset.current_employee_id.name,
            )
            asset.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('Asset return required — employee archived'),
                note=_(
                    'Employee %s has been archived but still holds asset %s (%s). '
                    'Please arrange return.'
                ) % (
                    asset.current_employee_id.name,
                    asset.code,
                    asset.name,
                ),
            )

            # Auto-return if configured
            if self.env.company.auto_return_on_employee_archive:
                assignment = self.env['asset.assignment'].search([
                    ('asset_id', '=', asset.id),
                    ('is_active', '=', True),
                ], limit=1)
                if assignment:
                    assignment.write({
                        'is_active': False,
                        'return_date': fields.Date.today(),
                        'condition_on_return': 'fair',
                    })
                    asset.write({
                        'state': 'available',
                        'current_employee_id': False,
                    })
                    asset._log_history(
                        event_type='return',
                        old_state='assigned',
                        new_state='available',
                        employee_id=asset.current_employee_id.id,
                        description=_('Auto-returned on employee archive by cron'),
                    )

    @api.model
    def get_dashboard_data(self):
        """Called by OWL dashboard component."""
        domain_base = [('company_id', 'in', self.env.companies.ids)]
        assets = self.search(domain_base)

        total = len(assets)
        available = len(assets.filtered(lambda a: a.state == 'available'))
        assigned = len(assets.filtered(lambda a: a.state == 'assigned'))
        scrapped_disposed = len(assets.filtered(lambda a: a.state in ('scrapped', 'disposed')))
        total_value = sum(assets.mapped('purchase_price'))
        net_book_value = sum(assets.mapped('residual_value'))

        pending_dep = self.env['asset.depreciation.line'].search_count([
            ('move_check', '=', False),
            ('depreciation_date', '<=', fields.Date.today()),
            ('asset_id.state', 'in', ['available', 'assigned']),
            ('company_id', 'in', self.env.companies.ids),
        ])

        # Category breakdown
        category_data = {}
        for asset in assets:
            cat = asset.category_id.name or _('Uncategorised')
            category_data[cat] = category_data.get(cat, 0) + 1

        return {
            'total': total,
            'available': available,
            'assigned': assigned,
            'scrapped_disposed': scrapped_disposed,
            'total_value': total_value,
            'net_book_value': net_book_value,
            'pending_depreciation': pending_dep,
            'by_category': [
                {'category': k, 'count': v}
                for k, v in sorted(category_data.items(), key=lambda x: -x[1])
            ],
        }
