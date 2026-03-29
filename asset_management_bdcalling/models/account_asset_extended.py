# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountAssetExtended(models.Model):
    _inherit = 'account.asset'

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
 


    # ─── State ───────────────────────────────────────────────────────────────

    asset_state = fields.Selection(
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

    original_location_id = fields.Many2one('stock.location', string="Original Location")


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


    notes = fields.Text(string='Notes')


    # ─── SQL Constraints ─────────────────────────────────────────────────────

    # _sql_constraints = [
    #     (
    #         'lot_unique',
    #         'UNIQUE(lot_id)',
    #         'A serial number can only be registered as one asset.',
    #     ),
    #     (
    #         'code_unique',
    #         'UNIQUE(code)',
    #         'Asset code must be globally unique.',
    #     ),
    # ]
    # @api.constrains('code')
    # def _check_code_unique(self):
    #     for rec in self:
    #         if rec.code:
    #             existing = self.search([
    #                 ('code', '=', rec.code),
    #                 ('id', '!=', rec.id)
    #             ], limit=1)
    #             if existing:
    #                 raise ValidationError("Asset code must be unique.")
    
    @api.constrains('lot_id')
    def _check_lot_unique(self):
        for rec in self:
            if rec.lot_id:
                existing = self.search([
                    ('lot_id', '=', rec.lot_id.id),
                    ('id', '!=', rec.id)
                ], limit=1)

                if existing:
                    raise ValidationError(
                        "A serial number can only be registered as one asset."
                    )

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

    
    # ─── ORM Overrides ───────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        seq_model = self.env['ir.sequence']

        for vals in vals_list:
            # Only generate code for real assets (must have product + lot)
            if not vals.get('code') and vals.get('lot_id'):
                code = seq_model.next_by_code('account.asset.code')

                if not code:
                    raise ValidationError(
                        "Sequence 'account.asset.code' is not configured."
                    )

                vals['code'] = code

        return super().create(vals_list)

    
    # def action_register(self):
    #     self.ensure_one()

    #     if self.asset_state != 'draft':
    #         raise UserError(_("Only draft assets can be registered"))

    #     if not self.product_id or not self.lot_id:
    #         raise UserError(_("Product and Serial Number required"))

    #     source_location = self.location_id or self.env.ref('stock.stock_location_stock')
    #     self.original_location_id = source_location

    #     scrap_location = self.env.ref(
    #         'stock.stock_location_scrap',
    #         raise_if_not_found=False
    #     )

    #     if not scrap_location:
    #         scrap_location = self.env['stock.location'].search([
    #             ('usage', '=', 'inventory')
    #         ], limit=1)

    #     if not scrap_location:
    #         raise UserError(_("No scrap location found."))

    #     move = self.env['stock.move'].create({
    #         'product_id': self.product_id.id,
    #         'product_uom_qty': 1,
    #         'product_uom': self.product_id.uom_id.id,
    #         'location_id': source_location.id,
    #         'location_dest_id': scrap_location.id,
    #         'description_picking': f'Asset Register: {self.name}',
    #     })

    #     move._action_confirm()
    #     move._action_assign()

    #     self.env['stock.move.line'].create({
    #         'move_id': move.id,
    #         'product_id': self.product_id.id,
    #         'qty_done': 1,
    #         'location_id': source_location.id,
    #         'location_dest_id': scrap_location.id,
    #         'lot_id': self.lot_id.id,
    #     })

    #     move._action_done()

    #     self.asset_state = 'available'

    def action_register(self):
        for rec in self:
            if rec.asset_state != 'draft':
                raise UserError(_("Only draft assets can be registered"))

            if not rec.product_id or not rec.lot_id:
                raise UserError(_("Product and Serial Number required"))

            source_location = rec.location_id or self.env.ref('stock.stock_location_stock')
            rec.original_location_id = source_location

            scrap_location = self.env.ref(
                'stock.stock_location_scrap',
                raise_if_not_found=False
            )

            if not scrap_location:
                scrap_location = self.env['stock.location'].search([
                    ('usage', '=', 'inventory')
                ], limit=1)

            if not scrap_location:
                raise UserError(_("No scrap location found."))

            move = self.env['stock.move'].create({
                'product_id': rec.product_id.id,
                'product_uom_qty': 1,
                'product_uom': rec.product_id.uom_id.id,
                'location_id': source_location.id,
                'location_dest_id': scrap_location.id,
                'description_picking': f'Asset Register: {rec.name}',
            })

            move._action_confirm()
            move._action_assign()

            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': rec.product_id.id,
                'qty_done': 1,
                'location_id': source_location.id,
                'location_dest_id': scrap_location.id,
                'lot_id': rec.lot_id.id,
            })

            move._action_done()

            rec.asset_state = 'available'

    def action_unregister(self):
        self.ensure_one()
        
        if self.asset_state != 'available':
            raise UserError(_("Only available assets can be unregistered"))
        
        if not self.product_id or not self.lot_id:
            raise UserError(_("Product and Serial Number required"))
        
        # Find where the asset currently is (scrap location or wherever it was moved to)
        quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', '=', self.lot_id.id),
            ('quantity', '>', 0)
        ], limit=1)
        
        if not quant:
            raise UserError(_("Asset not found in stock location"))
        
        source_location = quant.location_id
        
        # Use the original location if available, otherwise use a default location
        destination_location = self.original_location_id or self.location_id or self.env.ref('stock.stock_location_stock')
        
        # Create reverse move
        move = self.env['stock.move'].create({
            'product_id': self.product_id.id,
            'product_uom_qty': 1,
            'product_uom': self.product_id.uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': destination_location.id,
            'description_picking': f'Asset Unregister: {self.name}',
        })
        
        move._action_confirm()
        move._action_assign()
        
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': self.product_id.id,
            'qty_done': 1,
            'location_id': source_location.id,
            'location_dest_id': destination_location.id,
            'lot_id': self.lot_id.id,
        })
        
        move._action_done()
        
        # Reset state to draft
        self.asset_state = 'draft'
        
        # Clear the original location reference if desired
        # self.original_location_id = False
    def action_auto_create_from_product_serials(self):
        """
        Find every stock.lot for self.product_id that is not yet claimed by
        any asset record and create one draft account.asset per lot.
        The current record's category / accounting config is copied to each child.
        """
        self.ensure_one()

        if not self.product_id:
            raise UserError(_('Please select a Product first.'))

        all_lots = self.env['stock.lot'].search([
            ('product_id', '=', self.product_id.id),
        ])
        if not all_lots:
            raise UserError(_(
                'Product "%s" has no serial numbers recorded in inventory.'
            ) % self.product_id.name)

        # Lots already claimed by any other asset (draft or live)
        taken_lot_ids = self.env['account.asset'].search([
            ('lot_id',      '!=', False),
            ('product_id',  '=',  self.product_id.id),
            ('id',          '!=', self.id),
        ]).mapped('lot_id').ids

        free_lots = all_lots.filtered(lambda l: l.id not in taken_lot_ids)
        if not free_lots:
            raise UserError(_(
                'All serial numbers for "%s" already have asset records.'
            ) % self.product_id.name)

        created = self.env['account.asset']

        for lot in free_lots:
            asset = self.env['account.asset'].create({
                # Identity
                'name':         f'{self.product_id.name} [{lot.name}]',
                'product_id':   self.product_id.id,
                'lot_id':       lot.id,
                'company_id':   self.company_id.id,
                'asset_state':  'draft',
                # Category / accounting — copied from the current record if set
                'model_id':      self.model_id.id if self.model_id else False,
                'original_value': self.original_value or 0.0,
                'acquisition_date': self.acquisition_date or fields.Date.today(),
                'account_asset_id':
                    self.account_asset_id.id
                    if self.account_asset_id else False,
                'account_depreciation_id':
                    self.account_depreciation_id.id
                    if self.account_depreciation_id else False,
                'account_depreciation_expense_id':
                    self.account_depreciation_expense_id.id
                    if self.account_depreciation_expense_id else False,
                'journal_id':
                    self.journal_id.id if self.journal_id else False,
                'method':        self.method        or False,
                'method_number': self.method_number or 0,
                'method_period': self.method_period or '1',
            })
            created |= asset

        created.action_register()

        _logger.info(
            'AMS: Auto-created %d draft assets for product %s',
            len(created), self.product_id.name,
        )

        if len(created) == 1:
            return {
                'type':      'ir.actions.act_window',
                'name':      _('Draft Asset'),
                'res_model': 'account.asset',
                'res_id':    created.id,
                'view_mode': 'form',
                'target':    'current',
            }
        return {
            'type':      'ir.actions.act_window',
            'name':      _('%d Draft Assets Created') % len(created),
            'res_model': 'account.asset',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', created.ids)],
            'target':    'current',
        }
    def action_assign(self):
        """Open the assign wizard."""
        self.ensure_one()
        if self.asset_state != 'available':
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
        if self.asset_state != 'assigned':
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
        if self.asset_state not in ('available', 'assigned'):
            raise UserError(_('Only available or assigned assets can be scrapped.'))
        old_state = self.asset_state
        self.write({'asset_state': 'scrapped', 'current_employee_id': False})
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
        if self.asset_state not in ('available', 'assigned'):
            raise UserError(_('Only available or assigned assets can be disposed.'))
        old_state = self.asset_state
        self.write({'asset_state': 'disposed', 'current_employee_id': False})
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
            'new_state': new_state or self.asset_state,
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
        locked_lots = self.env['account.asset'].search([
            ('lot_id', '!=', False),
            ('asset_state', '!=', 'draft'),
            ('id', 'not in', self.ids),
        ]).mapped('lot_id')

        for rec in self:
            domain = [('product_id', '=', rec.product_id.id)] if rec.product_id else []
            product_lots = self.env['stock.lot'].search(domain)
            rec.available_lot_ids = product_lots - locked_lots

    

    # ─── Dashboard Data ──────────────────────────────────────────────────────

    # @api.model
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
            ('asset_state', '=', 'assigned'),
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
                        'asset_state': 'available',
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
        """Called by the OWL AssetDashboard component."""
        company_ids = self.env.companies.ids

        # AMS assets are identified by lot_id being set.
        # sudo() is used so the multi-company rule does not silently hide
        # assets from companies the user can switch to.
        assets = self.sudo().search([
            ('lot_id',     '!=', False),
            ('asset_state', 'not in', ['draft']),
            ('company_id', 'in', company_ids),
        ])

        total             = len(assets)
        available         = sum(1 for a in assets if a.asset_state == 'available')
        assigned          = sum(1 for a in assets if a.asset_state == 'assigned')
        scrapped_disposed = sum(
            1 for a in assets if a.asset_state in ('scrapped', 'disposed')
        )

        active_assets     = assets.filtered(
            lambda a: a.asset_state in ('available', 'assigned')
        )
        
        # # Native fields: original_value (set before validate), value_residual (computed)
        # total_value       = sum(assets.mapped('original_value'))
        # net_book_value    = sum(assets.mapped('value_residual'))
        # total_depreciated = total_value - net_book_value

        # # Pending draft depreciation moves due today or earlier
        # pending_depreciation = self.env['account.move'].sudo().search_count([
        #     ('asset_id', 'in', assets.ids),
        #     ('state',    '=', 'draft'),
        #     ('date',     '<=', fields.Date.today()),
        # ])

        total_value       = sum(active_assets.mapped('original_value'))
        net_book_value    = sum(active_assets.mapped('value_residual'))
        total_depreciated = total_value - net_book_value

        # Pending draft depreciation moves — also scope to active assets only
        pending_depreciation = self.env['account.move'].sudo().search_count([
            ('asset_id', 'in', active_assets.ids),
            ('state',    '=', 'draft'),
            ('date',     '<=', fields.Date.today()),
        ])

        # Category breakdown by native model_id
        category_data = {}
        for asset in assets:
            cat = asset.model_id.name or _('Uncategorised')
            category_data[cat] = category_data.get(cat, 0) + 1

        # Last 10 assignments
        recent = self.env['asset.assignment'].sudo().search(
            [('company_id', 'in', company_ids)],
            order='assign_date desc',
            limit=10,
        )
        recent_assignments = [
            {
                'id':         a.id,
                'asset':      a.asset_id.name or '',
                'asset_code': a.asset_id.code or '',
                'employee':   a.employee_id.name or '',
                'date':       str(a.assign_date) if a.assign_date else '',
                'is_active':  a.is_active,
            }
            for a in recent
        ]

        return {
            'total':                total,
            'available':            available,
            'assigned':             assigned,
            'scrapped_disposed':    scrapped_disposed,
            'total_value':          total_value,
            'net_book_value':       net_book_value,
            'total_depreciated':    total_depreciated,
            'pending_depreciation': pending_depreciation,
            'by_category': [
                {'category': k, 'count': v}
                for k, v in sorted(
                    category_data.items(), key=lambda x: -x[1]
                )
            ],
            'recent_assignments': recent_assignments,
        }
