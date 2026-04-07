# # -*- coding: utf-8 -*-
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError, ValidationError
# import logging

# _logger = logging.getLogger(__name__)

# class AccountAssetExtended(models.Model):
#     _inherit = 'account.asset'

#     # ─── Identity ────────────────────────────────────────────────────────────

#     name = fields.Char(
#         string='Asset Name',
#         compute='_compute_name',
#         store=True,
#         readonly=False,
#     )

#     code = fields.Char(
#         string='Asset Code',
#         readonly=True,
#         copy=False,
#         index=True,
#     )

#     company_id = fields.Many2one(
#         'res.company',
#         string='Company',
#         required=True,
#         default=lambda self: self.env.company,
#         tracking=True,
#     )

#     active = fields.Boolean(string='Active', default=True)

#     # ─── Product & Serial ────────────────────────────────────────────────────

#     product_id = fields.Many2one(
#         'product.product',
#         string='Product',
#         required=True,
#         tracking=True,
#         domain="[('is_asset', 'in', [True])]",
#     )

#     lot_id = fields.Many2one(
#         'stock.lot',
#         string='Serial Number (Lot)',
#         required=True,
#         tracking=True,
#         domain="[('id', 'in', available_lot_ids)]",
#     )

#     available_lot_ids = fields.Many2many(
#         'stock.lot',
#         string='Available Serials',
#         compute='_compute_available_lot_ids',
#         readonly=True,
#     )
 


#     # ─── State ───────────────────────────────────────────────────────────────

#     asset_state = fields.Selection(
#         selection=[
#             ('draft', 'Draft'),
#             ('available', 'Available'),
#             ('assigned', 'Assigned'),
#             ('returned', 'Returned'),
#             ('scrapped', 'Scrapped'),
#             ('disposed', 'Disposed'),
#         ],
#         string='Status',
#         default='draft',
#         required=True,
#         tracking=True,
#         index=True,
#     )

#     # ─── Dates & Financials ──────────────────────────────────────────────────

#     purchase_date = fields.Date(string='Purchase Date', tracking=True)
#     registration_date = fields.Date(string='Registration Date', readonly=True)
#     purchase_price = fields.Monetary(
#         string='Purchase Price',
#         currency_field='currency_id',
#         required=True,
#         tracking=True,
#         groups='account.group_account_manager,custom_asset_management.group_asset_manager',
#     )

#     currency_id = fields.Many2one(
#         'res.currency',
#         string='Currency',
#         required=True,
#         default=lambda self: self.env.company.currency_id,
#     )

#     # ─── Location & Assignment ───────────────────────────────────────────────

#     location_id = fields.Many2one(
#         'stock.location',
#         string='Asset Location',
#     )

#     current_employee_id = fields.Many2one(
#         'hr.employee',
#         string='Assigned To',
#         tracking=True,
#         domain="[('company_id', '=', company_id)]",
#     )

#     original_location_id = fields.Many2one('stock.location', string="Original Location")


#     assignment_ids = fields.One2many(
#         'asset.assignment',
#         'asset_id',
#         string='Assignment History',
#     )

#     history_ids = fields.One2many(
#         'asset.history',
#         'asset_id',
#         string='Lifecycle History',
#     )


#     notes = fields.Text(string='Notes')

#     vendor_bill_line_id = fields.Many2one(
#         'account.move.line',
#         string='Vendor Bill Line',
       
#     )

#     register_move_id = fields.Many2one(
#         'account.move',
#         string='Register Journal Entry',
       
#     )


#     # ─── SQL Constraints ─────────────────────────────────────────────────────

#     # _sql_constraints = [
#     #     (
#     #         'lot_unique',
#     #         'UNIQUE(lot_id)',
#     #         'A serial number can only be registered as one asset.',
#     #     ),
#     #     (
#     #         'code_unique',
#     #         'UNIQUE(code)',
#     #         'Asset code must be globally unique.',
#     #     ),
#     # ]
#     # @api.constrains('code')
#     # def _check_code_unique(self):
#     #     for rec in self:
#     #         if rec.code:
#     #             existing = self.search([
#     #                 ('code', '=', rec.code),
#     #                 ('id', '!=', rec.id)
#     #             ], limit=1)
#     #             if existing:
#     #                 raise ValidationError("Asset code must be unique.")
    
#     @api.constrains('lot_id')
#     def _check_lot_unique(self):
#         for rec in self:
#             if rec.lot_id:
#                 existing = self.search([
#                     ('lot_id', '=', rec.lot_id.id),
#                     ('id', '!=', rec.id)
#                 ], limit=1)

#                 if existing:
#                     raise ValidationError(
#                         "A serial number can only be registered as one asset."
#                     )

#     # ─── Compute Methods ─────────────────────────────────────────────────────
#     @api.depends('product_id', 'lot_id')
#     def _compute_name(self):
#         for rec in self:
#             if rec.product_id and rec.lot_id:
#                 rec.name = f'{rec.product_id.name} [{rec.lot_id.name}]'
#             elif rec.product_id:
#                 rec.name = rec.product_id.name
#             else:
#                 rec.name = rec.name or _('New Asset')

    
#     # ─── ORM Overrides ───────────────────────────────────────────────────────

#     @api.model_create_multi
#     def create(self, vals_list):
#         seq_model = self.env['ir.sequence']

#         for vals in vals_list:
#             # Only generate code for real assets (must have product + lot)
#             if not vals.get('code') and vals.get('lot_id'):
#                 code = seq_model.next_by_code('account.asset.code')

#                 if not code:
#                     raise ValidationError(
#                         "Sequence 'account.asset.code' is not configured."
#                     )

#                 vals['code'] = code

#         return super().create(vals_list)

    
#     # def action_register(self):
#     #     self.ensure_one()

#     #     if self.asset_state != 'draft':
#     #         raise UserError(_("Only draft assets can be registered"))

#     #     if not self.product_id or not self.lot_id:
#     #         raise UserError(_("Product and Serial Number required"))

#     #     source_location = self.location_id or self.env.ref('stock.stock_location_stock')
#     #     self.original_location_id = source_location

#     #     scrap_location = self.env.ref(
#     #         'stock.stock_location_scrap',
#     #         raise_if_not_found=False
#     #     )

#     #     if not scrap_location:
#     #         scrap_location = self.env['stock.location'].search([
#     #             ('usage', '=', 'inventory')
#     #         ], limit=1)

#     #     if not scrap_location:
#     #         raise UserError(_("No scrap location found."))

#     #     move = self.env['stock.move'].create({
#     #         'product_id': self.product_id.id,
#     #         'product_uom_qty': 1,
#     #         'product_uom': self.product_id.uom_id.id,
#     #         'location_id': source_location.id,
#     #         'location_dest_id': scrap_location.id,
#     #         'description_picking': f'Asset Register: {self.name}',
#     #     })

#     #     move._action_confirm()
#     #     move._action_assign()

#     #     self.env['stock.move.line'].create({
#     #         'move_id': move.id,
#     #         'product_id': self.product_id.id,
#     #         'qty_done': 1,
#     #         'location_id': source_location.id,
#     #         'location_dest_id': scrap_location.id,
#     #         'lot_id': self.lot_id.id,
#     #     })

#     #     move._action_done()

#     #     self.asset_state = 'available'

#     def action_register(self):
#         for rec in self:
#             if rec.asset_state != 'draft':
#                 raise UserError(_("Only draft assets can be registered"))

#             if not rec.product_id or not rec.lot_id:
#                 raise UserError(_("Product and Serial Number required"))

#             source_location = rec.location_id or self.env.ref('stock.stock_location_stock')
#             rec.original_location_id = source_location

#             scrap_location = self.env.ref(
#                 'stock.stock_location_scrap',
#                 raise_if_not_found=False
#             )

#             if not scrap_location:
#                 scrap_location = self.env['stock.location'].search([
#                     ('usage', '=', 'inventory')
#                 ], limit=1)

#             if not scrap_location:
#                 raise UserError(_("No scrap location found."))

#             move = self.env['stock.move'].create({
#                 'product_id': rec.product_id.id,
#                 'product_uom_qty': 1,
#                 'product_uom': rec.product_id.uom_id.id,
#                 'location_id': source_location.id,
#                 'location_dest_id': scrap_location.id,
#                 'description_picking': f'Asset Register: {rec.name}',
#             })

#             move._action_confirm()
#             move._action_assign()

#             self.env['stock.move.line'].create({
#                 'move_id': move.id,
#                 'product_id': rec.product_id.id,
#                 'qty_done': 1,
#                 'location_id': source_location.id,
#                 'location_dest_id': scrap_location.id,
#                 'lot_id': rec.lot_id.id,
#             })

#             move._action_done()

#             rec._create_asset_account_move()

#             rec.asset_state = 'available'

#     def action_unregister(self):
#         self.ensure_one()
        
#         if self.asset_state != 'available':
#             raise UserError(_("Only available assets can be unregistered"))
        
#         if not self.product_id or not self.lot_id:
#             raise UserError(_("Product and Serial Number required"))
        
#         # Find where the asset currently is (scrap location or wherever it was moved to)
#         quant = self.env['stock.quant'].search([
#             ('product_id', '=', self.product_id.id),
#             ('lot_id', '=', self.lot_id.id),
#             ('quantity', '>', 0)
#         ], limit=1)
        
#         if not quant:
#             raise UserError(_("Asset not found in stock location"))
        
#         source_location = quant.location_id
        
#         # Use the original location if available, otherwise use a default location
#         destination_location = self.original_location_id or self.location_id or self.env.ref('stock.stock_location_stock')
        
#         # Create reverse move
#         move = self.env['stock.move'].create({
#             'product_id': self.product_id.id,
#             'product_uom_qty': 1,
#             'product_uom': self.product_id.uom_id.id,
#             'location_id': source_location.id,
#             'location_dest_id': destination_location.id,
#             'description_picking': f'Asset Unregister: {self.name}',
#         })
        
#         move._action_confirm()
#         move._action_assign()
        
#         self.env['stock.move.line'].create({
#             'move_id': move.id,
#             'product_id': self.product_id.id,
#             'qty_done': 1,
#             'location_id': source_location.id,
#             'location_dest_id': destination_location.id,
#             'lot_id': self.lot_id.id,
#         })
        
#         move._action_done()

#         self._create_asset_reverse_move()
        
#         # Reset state to draft
#         self.asset_state = 'draft'
        
#         # Clear the original location reference if desired
#         # self.original_location_id = False
#     def action_auto_create_from_product_serials(self):
#         """
#         Find every stock.lot for self.product_id that is not yet claimed by
#         any asset record and create one draft account.asset per lot.
#         The current record's category / accounting config is copied to each child.
#         """
#         self.ensure_one()

#         if not self.product_id:
#             raise UserError(_('Please select a Product first.'))
        
#         # if not self.vendor_bill_line_id:
#         #     raise UserError(_('Please select a Vendor Bill Line.'))

#         all_lots = self.env['stock.lot'].search([
#             ('product_id', '=', self.product_id.id),
#         ])

#         if not all_lots:
#             raise UserError(_(
#                 'Product "%s" has no serial numbers recorded in inventory.'
#             ) % self.product_id.name)

#         # Lots already claimed by any other asset (draft or live)
#         taken_lot_ids = self.env['account.asset'].search([
#             ('lot_id',      '!=', False),
#             ('product_id',  '=',  self.product_id.id),
#             ('id',          '!=', self.id),
#         ]).mapped('lot_id').ids

#         free_lots = all_lots.filtered(lambda l: l.id not in taken_lot_ids)
#         if not free_lots:
#             raise UserError(_(
#                 'All serial numbers for "%s" already have asset records.'
#             ) % self.product_id.name)

#         # ✅ PRICE DISTRIBUTION
#         bill_line = self.vendor_bill_line_id
#         total_qty = bill_line.quantity
#         total_price = bill_line.price_subtotal

#         if total_qty <= 0:
#             raise UserError(_("Invalid quantity in bill line"))

#         unit_price = total_price / total_qty

#         created = self.env['account.asset']

#         for lot in free_lots:
#             asset = self.env['account.asset'].create({
#                 # Identity
#                 'name':         f'{self.product_id.name} [{lot.name}]',
#                 'product_id':   self.product_id.id,
#                 'lot_id':       lot.id,
#                 'company_id':   self.company_id.id,
#                 'asset_state':  'draft',
#                  # ✅ VALUE FROM BILL
#                 'original_value': unit_price,
#                 'purchase_price': unit_price,

#                 'vendor_bill_line_id': bill_line.id,
#                 # Category / accounting — copied from the current record if set
#                 'model_id':      self.model_id.id if self.model_id else False,
#                 # 'original_value': self.original_value or 0.0,
#                 'acquisition_date': self.acquisition_date or fields.Date.today(),
#                 'account_asset_id':
#                     self.account_asset_id.id
#                     if self.account_asset_id else False,
#                 'account_depreciation_id':
#                     self.account_depreciation_id.id
#                     if self.account_depreciation_id else False,
#                 'account_depreciation_expense_id':
#                     self.account_depreciation_expense_id.id
#                     if self.account_depreciation_expense_id else False,
#                 'journal_id':
#                     self.journal_id.id if self.journal_id else False,
#                 'method':        self.method        or False,
#                 'method_number': self.method_number or 0,
#                 'method_period': self.method_period or '1',
#             })
#             created |= asset

#             created.action_register()

#         _logger.info(
#             'AMS: Auto-created %d draft assets for product %s',
#             len(created), self.product_id.name,
#         )

#         if len(created) == 1:
#             return {
#                 'type':      'ir.actions.act_window',
#                 'name':      _('Draft Asset'),
#                 'res_model': 'account.asset',
#                 'res_id':    created.id,
#                 'view_mode': 'form',
#                 'target':    'current',
#             }
#         return {
#             'type':      'ir.actions.act_window',
#             'name':      _('%d Draft Assets Created') % len(created),
#             'res_model': 'account.asset',
#             'view_mode': 'list,form',
#             'domain':    [('id', 'in', created.ids)],
#             'target':    'current',
#         }
#     def _create_asset_account_move(self):
#         self.ensure_one()

#         if not self.account_asset_id:
#             raise UserError(_("Set Fixed Asset Account"))

#         valuation_account = self.product_id.categ_id.property_stock_valuation_account_id

#         if not valuation_account:
#             raise UserError(_("No Stock Valuation Account found"))

#         move = self.env['account.move'].create({
#             'journal_id': self.journal_id.id,
#             'date': fields.Date.today(),
#             'ref': f'Asset Register: {self.name}',
#             'line_ids': [
#                 (0, 0, {
#                     'name': self.name,
#                     'account_id': self.account_asset_id.id,
#                     'debit': self.original_value,
#                     'credit': 0,
#                 }),
#                 (0, 0, {
#                     'name': self.name,
#                     'account_id': valuation_account.id,
#                     'credit': self.original_value,
#                     'debit': 0,
#                 }),
#             ]
#         })

#         move.action_post()

#         self.register_move_id = move.id

#     def _create_asset_reverse_move(self):
#         self.ensure_one()

#         valuation_account = self.product_id.categ_id.property_stock_valuation_account_id

#         move = self.env['account.move'].create({
#             'journal_id': self.journal_id.id,
#             'date': fields.Date.today(),
#             'ref': f'Asset Unregister: {self.name}',
#             'line_ids': [
#                 (0, 0, {
#                     'name': self.name,
#                     'account_id': valuation_account.id,
#                     'debit': self.original_value,
#                     'credit': 0,
#                 }),
#                 (0, 0, {
#                     'name': self.name,
#                     'account_id': self.account_asset_id.id,
#                     'credit': self.original_value,
#                     'debit': 0,
#                 }),
#             ]
#         })

#         move.action_post()

#     def action_assign(self):
#         """Open the assign wizard."""
#         self.ensure_one()
#         if self.asset_state != 'available':
#             raise UserError(_('Only assets in "Available" state can be assigned.'))
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Assign Asset'),
#             'res_model': 'asset.assign.wizard',
#             'view_mode': 'form',
#             'target': 'new',
#             'context': {'default_asset_id': self.id},
#         }

#     def action_return(self):
#         """Open the return wizard."""
#         self.ensure_one()
#         if self.asset_state != 'assigned':
#             raise UserError(_('Only assigned assets can be returned.'))
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Return Asset'),
#             'res_model': 'asset.return.wizard',
#             'view_mode': 'form',
#             'target': 'new',
#             'context': {'default_asset_id': self.id},
#         }

#     def action_scrap(self):
#         """Scrap the asset — available or assigned."""
#         self.ensure_one()
#         if self.asset_state not in ('available', 'assigned'):
#             raise UserError(_('Only available or assigned assets can be scrapped.'))
#         old_state = self.asset_state
#         self.write({'asset_state': 'scrapped', 'current_employee_id': False})
#         self._log_history(
#             event_type='scrap',
#             old_state=old_state,
#             new_state='scrapped',
#             description=_('Asset scrapped by %s') % self.env.user.name,
#         )
#         return True

#     def action_dispose(self):
#         """Dispose the asset — available or assigned."""
#         self.ensure_one()
#         if self.asset_state not in ('available', 'assigned'):
#             raise UserError(_('Only available or assigned assets can be disposed.'))
#         old_state = self.asset_state
#         self.write({'asset_state': 'disposed', 'current_employee_id': False})
#         self._log_history(
#             event_type='dispose',
#             old_state=old_state,
#             new_state='disposed',
#             description=_('Asset disposed by %s') % self.env.user.name,
#         )
#         return True

#     # ─── History Logging ─────────────────────────────────────────────────────

#     def _log_history(self, event_type, old_state=None, new_state=None,
#                      employee_id=None, description=None, metadata=None):
#         """Append an immutable history record for every state transition."""
#         self.env['asset.history'].sudo().create({
#             'asset_id': self.id,
#             'event_type': event_type,
#             'event_date': fields.Datetime.now(),
#             'old_state': old_state or self._origin.state,
#             'new_state': new_state or self.asset_state,
#             'employee_id': employee_id,
#             'user_id': self.env.uid,
#             'description': description or _(
#                 'State changed: %s → %s'
#             ) % (old_state, new_state),
#             'metadata': metadata or {},
#             'company_id': self.company_id.id,
#         })

#     # ─── available lot ids ───────────────────────────────────────────────
#     @api.depends('product_id')
#     def _compute_available_lot_ids(self):
#         """
#         Returns lots that are NOT currently locked by a non-draft asset.
#         A lot is considered free when:
#           - no asset references it, OR
#           - the only referencing asset is this record itself (edit mode), OR
#           - the referencing asset is in state 'draft' (unregistered).
#         """
#         # Lots locked by active assets (excluding this record)
#         locked_lots = self.env['account.asset'].search([
#             ('lot_id', '!=', False),
#             ('asset_state', '!=', 'draft'),
#             ('id', 'not in', self.ids),
#         ]).mapped('lot_id')

#         for rec in self:
#             domain = [('product_id', '=', rec.product_id.id)] if rec.product_id else []
#             product_lots = self.env['stock.lot'].search(domain)
#             rec.available_lot_ids = product_lots - locked_lots

    

#     # ─── Dashboard Data ──────────────────────────────────────────────────────

#     # @api.model
#     def _cron_check_archived_employee_assets(self):
#         """
#         Daily cron: find assets still assigned to archived employees and
#         create a return activity on each, notifying the Asset Manager.
#         """
#         archived_employees = self.env['hr.employee'].with_context(active_test=False).search([
#             ('active', '=', False),
#         ])
#         if not archived_employees:
#             return

#         assets = self.search([
#             ('current_employee_id', 'in', archived_employees.ids),
#             ('asset_state', '=', 'assigned'),
#         ])

#         activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
#         for asset in assets:
#             _logger.warning(
#                 'AMS: Asset %s is still assigned to archived employee %s',
#                 asset.code,
#                 asset.current_employee_id.name,
#             )
#             asset.activity_schedule(
#                 activity_type_id=activity_type.id if activity_type else False,
#                 summary=_('Asset return required — employee archived'),
#                 note=_(
#                     'Employee %s has been archived but still holds asset %s (%s). '
#                     'Please arrange return.'
#                 ) % (
#                     asset.current_employee_id.name,
#                     asset.code,
#                     asset.name,
#                 ),
#             )

#             # Auto-return if configured
#             if self.env.company.auto_return_on_employee_archive:
#                 assignment = self.env['asset.assignment'].search([
#                     ('asset_id', '=', asset.id),
#                     ('is_active', '=', True),
#                 ], limit=1)
#                 if assignment:
#                     assignment.write({
#                         'is_active': False,
#                         'return_date': fields.Date.today(),
#                         'condition_on_return': 'fair',
#                     })
#                     asset.write({
#                         'asset_state': 'available',
#                         'current_employee_id': False,
#                     })
#                     asset._log_history(
#                         event_type='return',
#                         old_state='assigned',
#                         new_state='available',
#                         employee_id=asset.current_employee_id.id,
#                         description=_('Auto-returned on employee archive by cron'),
#                     )

#     @api.model
#     def get_dashboard_data(self):
#         """Called by the OWL AssetDashboard component."""
#         company_ids = self.env.companies.ids

#         # AMS assets are identified by lot_id being set.
#         # sudo() is used so the multi-company rule does not silently hide
#         # assets from companies the user can switch to.
#         assets = self.sudo().search([
#             ('lot_id',     '!=', False),
#             ('asset_state', 'not in', ['draft']),
#             ('company_id', 'in', company_ids),
#         ])

#         total             = len(assets)
#         available         = sum(1 for a in assets if a.asset_state == 'available')
#         assigned          = sum(1 for a in assets if a.asset_state == 'assigned')
#         scrapped_disposed = sum(
#             1 for a in assets if a.asset_state in ('scrapped', 'disposed')
#         )

#         active_assets     = assets.filtered(
#             lambda a: a.asset_state in ('available', 'assigned')
#         )
        
#         # # Native fields: original_value (set before validate), value_residual (computed)
#         # total_value       = sum(assets.mapped('original_value'))
#         # net_book_value    = sum(assets.mapped('value_residual'))
#         # total_depreciated = total_value - net_book_value

#         # # Pending draft depreciation moves due today or earlier
#         # pending_depreciation = self.env['account.move'].sudo().search_count([
#         #     ('asset_id', 'in', assets.ids),
#         #     ('state',    '=', 'draft'),
#         #     ('date',     '<=', fields.Date.today()),
#         # ])

#         total_value       = sum(active_assets.mapped('original_value'))
#         net_book_value    = sum(active_assets.mapped('value_residual'))
#         total_depreciated = total_value - net_book_value

#         # Pending draft depreciation moves — also scope to active assets only
#         pending_depreciation = self.env['account.move'].sudo().search_count([
#             ('asset_id', 'in', active_assets.ids),
#             ('state',    '=', 'draft'),
#             ('date',     '<=', fields.Date.today()),
#         ])

#         # Category breakdown by native model_id
#         category_data = {}
#         for asset in assets:
#             cat = asset.model_id.name or _('Uncategorised')
#             category_data[cat] = category_data.get(cat, 0) + 1

#         # Last 10 assignments
#         recent = self.env['asset.assignment'].sudo().search(
#             [('company_id', 'in', company_ids)],
#             order='assign_date desc',
#             limit=10,
#         )
#         recent_assignments = [
#             {
#                 'id':         a.id,
#                 'asset':      a.asset_id.name or '',
#                 'asset_code': a.asset_id.code or '',
#                 'employee':   a.employee_id.name or '',
#                 'date':       str(a.assign_date) if a.assign_date else '',
#                 'is_active':  a.is_active,
#             }
#             for a in recent
#         ]

#         return {
#             'total':                total,
#             'available':            available,
#             'assigned':             assigned,
#             'scrapped_disposed':    scrapped_disposed,
#             'total_value':          total_value,
#             'net_book_value':       net_book_value,
#             'total_depreciated':    total_depreciated,
#             'pending_depreciation': pending_depreciation,
#             'by_category': [
#                 {'category': k, 'count': v}
#                 for k, v in sorted(
#                     category_data.items(), key=lambda x: -x[1]
#                 )
#             ],
#             'recent_assignments': recent_assignments,
#         }

# -*- coding: utf-8 -*-
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError, ValidationError
# import logging

# _logger = logging.getLogger(__name__)


# class AccountAssetExtended(models.Model):
#     _inherit = 'account.asset'

#     # ─── Identity ────────────────────────────────────────────────────────────

#     name = fields.Char(
#         string='Asset Name',
#         compute='_compute_name',
#         store=True,
#         readonly=False,
#     )

#     code = fields.Char(
#         string='Asset Code',
#         readonly=True,
#         copy=False,
#         index=True,
#     )

#     company_id = fields.Many2one(
#         'res.company',
#         string='Company',
#         required=True,
#         default=lambda self: self.env.company,
#         tracking=True,
#     )

#     active = fields.Boolean(string='Active', default=True)

#     # ─── Product & Serial ────────────────────────────────────────────────────

#     product_id = fields.Many2one(
#         'product.product',
#         string='Product',
#         required=True,
#         tracking=True,
#         domain="[('is_asset', 'in', [True])]",
#     )

#     lot_id = fields.Many2one(
#         'stock.lot',
#         string='Serial Number (Lot)',
#         required=True,
#         tracking=True,
#         domain="[('id', 'in', available_lot_ids)]",
#     )

#     available_lot_ids = fields.Many2many(
#         'stock.lot',
#         string='Available Serials',
#         compute='_compute_available_lot_ids',
#         readonly=True,
#     )

#     # ─── State ───────────────────────────────────────────────────────────────

#     asset_state = fields.Selection(
#         selection=[
#             ('draft',     'Draft'),
#             ('available', 'Available'),
#             ('assigned',  'Assigned'),
#             ('returned',  'Returned'),
#             ('scrapped',  'Scrapped'),
#             ('disposed',  'Disposed'),
#         ],
#         string='Status',
#         default='draft',
#         required=True,
#         tracking=True,
#         index=True,
#     )

#     # ─── Dates & Financials ──────────────────────────────────────────────────

#     purchase_date      = fields.Date(string='Purchase Date', tracking=True)
#     registration_date  = fields.Date(string='Registration Date', readonly=True)
#     purchase_price     = fields.Monetary(
#         string='Purchase Price',
#         currency_field='currency_id',
#         required=True,
#         tracking=True,
#         groups='account.group_account_manager,custom_asset_management.group_asset_manager',
#     )

#     currency_id = fields.Many2one(
#         'res.currency',
#         string='Currency',
#         required=True,
#         default=lambda self: self.env.company.currency_id,
#     )

#     # ─── Location & Assignment ───────────────────────────────────────────────

#     location_id = fields.Many2one('stock.location', string='Asset Location')
#     original_location_id = fields.Many2one('stock.location', string='Original Location')

#     current_employee_id = fields.Many2one(
#         'hr.employee',
#         string='Assigned To',
#         tracking=True,
#         domain="[('company_id', '=', company_id)]",
#     )

#     assignment_ids = fields.One2many('asset.assignment', 'asset_id', string='Assignment History')
#     history_ids    = fields.One2many('asset.history',    'asset_id', string='Lifecycle History')
#     notes          = fields.Text(string='Notes')

#     vendor_bill_line_id = fields.Many2one('account.move.line', string='Vendor Bill Line')
#     register_move_id    = fields.Many2one('account.move',      string='Register Journal Entry')

#     # ─── Constraints ─────────────────────────────────────────────────────────

#     @api.constrains('lot_id')
#     def _check_lot_unique(self):
#         for rec in self:
#             if rec.lot_id:
#                 existing = self.search([
#                     ('lot_id', '=', rec.lot_id.id),
#                     ('id',     '!=', rec.id),
#                 ], limit=1)
#                 if existing:
#                     raise ValidationError(
#                         "A serial number can only be registered as one asset."
#                     )

#     # ─── Compute ─────────────────────────────────────────────────────────────

#     @api.depends('product_id', 'lot_id')
#     def _compute_name(self):
#         for rec in self:
#             if rec.product_id and rec.lot_id:
#                 rec.name = f'{rec.product_id.name} [{rec.lot_id.name}]'
#             elif rec.product_id:
#                 rec.name = rec.product_id.name
#             else:
#                 rec.name = rec.name or _('New Asset')

#     @api.depends('product_id')
#     def _compute_available_lot_ids(self):
#         locked_lots = self.env['account.asset'].search([
#             ('lot_id',      '!=', False),
#             ('asset_state', '!=', 'draft'),
#             ('id',          'not in', self.ids),
#         ]).mapped('lot_id')

#         for rec in self:
#             domain = [('product_id', '=', rec.product_id.id)] if rec.product_id else []
#             product_lots = self.env['stock.lot'].search(domain)
#             rec.available_lot_ids = product_lots - locked_lots

#     # ─── ORM Overrides ───────────────────────────────────────────────────────

#     @api.model_create_multi
#     def create(self, vals_list):
#         seq_model = self.env['ir.sequence']
#         for vals in vals_list:
#             if not vals.get('code') and vals.get('lot_id'):
#                 code = seq_model.next_by_code('account.asset.code')
#                 if not code:
#                     raise ValidationError(
#                         "Sequence 'account.asset.code' is not configured."
#                     )
#                 vals['code'] = code
#         return super().create(vals_list)

#     # ─── action_register (model-level) ───────────────────────────────────────
#     # NOTE: This method is the direct-registration path used by
#     # action_auto_create_from_product_serials.  The wizard path
#     # (asset_register_wizard.py) calls validate() itself and is preferred
#     # for interactive use. Keep both consistent.

#     def action_register(self):
#         """
#         Register each asset in self:
#         1. Validate state and fields.
#         2. Check inventory availability.
#         3. Move serial from source/WH location → asset location (not scrap).
#         4. Create the accounting entry Dr: Fixed Asset / Cr: Stock Valuation.
#         5. Call validate() to generate the depreciation schedule.
#         6. Set registration_date and transition to 'available'.
#         7. Log an immutable history record.
#         """
#         for rec in self:
#             # ── Guard: only draft assets ──────────────────────────────────────
#             # BUG 1 fixed: this iterates individual records; the caller must
#             # pass individual assets, not a growing accumulated recordset.
#             if rec.asset_state != 'draft':
#                 raise UserError(_("Only draft assets can be registered"))

#             if not rec.product_id or not rec.lot_id:
#                 raise UserError(_("Product and Serial Number are required"))

#             # ── BUG 2 FIX: inventory availability check ───────────────────────
#             source_location = (
#                 rec.location_id
#                 or self.env.company.asset_location_id
#                 or self.env.ref('stock.stock_location_stock')
#             )
#             quant = self.env['stock.quant'].search([
#                 ('product_id', '=', rec.product_id.id),
#                 ('lot_id',     '=', rec.lot_id.id),
#                 ('location_id', '=', source_location.id),
#                 ('quantity',    '>',  0),
#             ], limit=1)
#             if not quant:
#                 # Fall back to any internal location that has the serial
#                 quant = self.env['stock.quant'].search([
#                     ('product_id', '=', rec.product_id.id),
#                     ('lot_id',     '=', rec.lot_id.id),
#                     ('quantity',   '>',  0),
#                 ], limit=1)
#                 if not quant:
#                     raise UserError(_(
#                         'Serial number "%s" is not in stock. '
#                         'Receive it into inventory first.'
#                     ) % rec.lot_id.name)
#                 source_location = quant.location_id

#             rec.original_location_id = source_location

#             # ── BUG 3 FIX: move to asset location, NOT scrap ──────────────────
#             asset_location = (
#                 self.env.company.asset_location_id
#                 or self.env.ref(
#                     'asset_management_bdcalling.asset_stock_location',
#                     raise_if_not_found=False,
#                 )
#             )
#             if not asset_location:
#                 raise UserError(_(
#                     'No default Asset Location configured. '
#                     'Go to Asset Management → Configuration → Settings.'
#                 ))

#             move = self.env['stock.move'].create({
#                 'product_id':          rec.product_id.id,
#                 'product_uom_qty':     1,
#                 'product_uom':         rec.product_id.uom_id.id,
#                 'location_id':         source_location.id,
#                 'location_dest_id':    asset_location.id,
#                 'description_picking': f'Asset Register: {rec.name}',
#                 'company_id':          rec.company_id.id,
#             })
#             move._action_confirm()
#             move._action_assign()
#             self.env['stock.move.line'].create({
#                 'move_id':          move.id,
#                 'product_id':       rec.product_id.id,
#                 'qty_done':         1,
#                 'location_id':      source_location.id,
#                 'location_dest_id': asset_location.id,
#                 'lot_id':           rec.lot_id.id,
#             })
#             move._action_done()

#             rec.location_id = asset_location

#             # ── Accounting: Dr Fixed Asset / Cr Stock Valuation ───────────────
#             rec._create_asset_account_move()

#             # ── BUG 4 FIX: call validate() to generate depreciation schedule ──
#             # validate() sets native state='open' and creates draft account.move
#             # entries for every depreciation period.  Only call when the
#             # accounting config is complete enough for validate() to succeed.
#             if (rec.account_asset_id
#                     and rec.account_depreciation_id
#                     and rec.account_depreciation_expense_id
#                     and rec.journal_id
#                     and rec.method
#                     and rec.method_number):
#                 try:
#                     rec.validate()
#                 except UserError:
#                     raise
#                 except Exception as exc:
#                     _logger.error(
#                         'AMS: validate() failed for asset %s: %s',
#                         rec.code, exc,
#                     )
#                     raise UserError(_(
#                         'Depreciation schedule generation failed for "%s".\n%s\n\n'
#                         'Verify the accounting configuration on the asset category.'
#                     ) % (rec.name, exc))
#             else:
#                 _logger.warning(
#                     'AMS: asset %s is missing accounting fields; '
#                     'depreciation schedule was NOT generated.',
#                     rec.code,
#                 )

#             # ── BUG 7 FIX: set registration_date and transition state ─────────
#             rec.write({
#                 'asset_state':       'available',
#                 'registration_date': fields.Date.today(),
#             })

#             # ── BUG 7 FIX: log immutable history record ───────────────────────
#             rec._log_history(
#                 event_type='register',
#                 old_state='draft',
#                 new_state='available',
#                 description=_('Asset registered by %s') % self.env.user.name,
#                 metadata={'source_location': source_location.complete_name},
#             )

#     # ─── action_unregister ───────────────────────────────────────────────────

#     def action_unregister(self):
#         self.ensure_one()

#         if self.asset_state != 'available':
#             raise UserError(_("Only available assets can be unregistered"))

#         if not self.product_id or not self.lot_id:
#             raise UserError(_("Product and Serial Number required"))

#         quant = self.env['stock.quant'].search([
#             ('product_id', '=', self.product_id.id),
#             ('lot_id',     '=', self.lot_id.id),
#             ('quantity',   '>',  0),
#         ], limit=1)

#         if not quant:
#             raise UserError(_("Asset serial number not found in any stock location."))

#         source_location = quant.location_id
#         destination_location = (
#             self.original_location_id
#             or self.location_id
#             or self.env.ref('stock.stock_location_stock')
#         )

#         move = self.env['stock.move'].create({
#             'product_id':          self.product_id.id,
#             'product_uom_qty':     1,
#             'product_uom':         self.product_id.uom_id.id,
#             'location_id':         source_location.id,
#             'location_dest_id':    destination_location.id,
#             'description_picking': f'Asset Unregister: {self.name}',
#             'company_id':          self.company_id.id,
#         })
#         move._action_confirm()
#         move._action_assign()
#         self.env['stock.move.line'].create({
#             'move_id':          move.id,
#             'product_id':       self.product_id.id,
#             'qty_done':         1,
#             'location_id':      source_location.id,
#             'location_dest_id': destination_location.id,
#             'lot_id':           self.lot_id.id,
#         })
#         move._action_done()

#         self._create_asset_reverse_move()

#         old_state = self.asset_state
#         self.write({
#             'asset_state':          'draft',
#             'registration_date':    False,
#             'original_location_id': False,
#         })

#         self._log_history(
#             event_type='unregister',
#             old_state=old_state,
#             new_state='draft',
#             description=_('Asset unregistered by %s') % self.env.user.name,
#         )

#     # ─── action_auto_create_from_product_serials ──────────────────────────────

#     def action_auto_create_from_product_serials(self):
#         """
#         Create one draft account.asset per unregistered serial number of
#         self.product_id, then immediately register each one.

#         BUG 1 FIX: action_register() is called on the individual `asset`
#         record, never on the accumulating `created` recordset.
#         """
#         self.ensure_one()

#         if not self.product_id:
#             raise UserError(_('Please select a Product first.'))

#         all_lots = self.env['stock.lot'].search([
#             ('product_id', '=', self.product_id.id),
#         ])
#         if not all_lots:
#             raise UserError(_(
#                 'Product "%s" has no serial numbers recorded in inventory.'
#             ) % self.product_id.name)

#         taken_lot_ids = self.env['account.asset'].search([
#             ('lot_id',     '!=', False),
#             ('product_id', '=',  self.product_id.id),
#             ('id',         '!=', self.id),
#         ]).mapped('lot_id').ids

#         free_lots = all_lots.filtered(lambda l: l.id not in taken_lot_ids)
#         if not free_lots:
#             raise UserError(_(
#                 'All serial numbers for "%s" already have asset records.'
#             ) % self.product_id.name)

#         # ── Price distribution from vendor bill line ──────────────────────────
#         bill_line = self.vendor_bill_line_id
#         if bill_line:
#             total_qty   = bill_line.quantity or 1
#             unit_price  = bill_line.price_subtotal / total_qty
#         else:
#             unit_price = self.original_value or self.purchase_price or 0.0

#         created = self.env['account.asset']

#         for lot in free_lots:
#             asset = self.env['account.asset'].create({
#                 'name':        f'{self.product_id.name} [{lot.name}]',
#                 'product_id':  self.product_id.id,
#                 'lot_id':      lot.id,
#                 'company_id':  self.company_id.id,
#                 'asset_state': 'draft',

#                 # Financial
#                 'original_value': unit_price,
#                 'purchase_price': unit_price,

#                 # Vendor bill reference
#                 'vendor_bill_line_id': bill_line.id if bill_line else False,

#                 # Category / accounting — copied from the current record
#                 'model_id':                       self.model_id.id if self.model_id else False,
#                 'acquisition_date':                self.acquisition_date or fields.Date.today(),
#                 'account_asset_id':                self.account_asset_id.id if self.account_asset_id else False,
#                 'account_depreciation_id':         self.account_depreciation_id.id if self.account_depreciation_id else False,
#                 'account_depreciation_expense_id': self.account_depreciation_expense_id.id if self.account_depreciation_expense_id else False,
#                 'journal_id':                      self.journal_id.id if self.journal_id else False,
#                 'method':                          self.method        or False,
#                 'method_number':                   self.method_number or 0,
#                 'method_period':                   self.method_period or '1',
#             })

#             # ── BUG 1 FIX: register THIS asset only, not the whole recordset ──
#             try:
#                 asset.action_register()
#                 created |= asset
#             except UserError as e:
#                 _logger.error(
#                     'AMS: auto-create registration failed for lot %s: %s',
#                     lot.name, e,
#                 )
#                 # Surface the first failure; partial rollback handled by Odoo
#                 raise

#         _logger.info(
#             'AMS: auto-created and registered %d assets for product %s',
#             len(created), self.product_id.name,
#         )

#         if len(created) == 1:
#             return {
#                 'type':      'ir.actions.act_window',
#                 'name':      _('Asset'),
#                 'res_model': 'account.asset',
#                 'res_id':    created.id,
#                 'view_mode': 'form',
#                 'target':    'current',
#             }
#         return {
#             'type':      'ir.actions.act_window',
#             'name':      _('%d Assets Created') % len(created),
#             'res_model': 'account.asset',
#             'view_mode': 'list,form',
#             'domain':    [('id', 'in', created.ids)],
#             'target':    'current',
#         }

#     # ─── Journal entry helpers ────────────────────────────────────────────────

#     def _create_asset_account_move(self):
#         """
#         Dr: Fixed Asset Account  (account_asset_id)
#         Cr: Stock Valuation Account  (property_stock_valuation_account_id)

#         BUG 5 FIX: guard journal_id
#         BUG 6 FIX: guard valuation account
#         """
#         self.ensure_one()

#         # BUG 5 FIX
#         if not self.journal_id:
#             raise UserError(_(
#                 'Asset "%s" has no journal configured. '
#                 'Set it on the asset category before registering.'
#             ) % (self.code or self.name))

#         # BUG 5 FIX (account)
#         if not self.account_asset_id:
#             raise UserError(_(
#                 'Asset "%s" has no Fixed Asset Account configured.'
#             ) % (self.code or self.name))

#         # BUG 6 FIX
#         valuation_account = self.product_id.categ_id.property_stock_valuation_account_id
#         if not valuation_account:
#             raise UserError(_(
#                 'Product category "%s" has no Stock Valuation Account. '
#                 'Go to Inventory → Configuration → Product Categories and set it.'
#             ) % self.product_id.categ_id.name)

#         value = self.original_value or self.purchase_price or 0.0
#         if not value:
#             _logger.warning(
#                 'AMS: asset %s has zero value; journal entry will be zero-amount.',
#                 self.code,
#             )

#         move = self.env['account.move'].create({
#             'journal_id': self.journal_id.id,
#             'date':       fields.Date.today(),
#             'ref':        f'Asset Register: {self.name}',
#             'line_ids': [
#                 (0, 0, {
#                     'name':       self.name,
#                     'account_id': self.account_asset_id.id,
#                     'debit':      value,
#                     'credit':     0.0,
#                 }),
#                 (0, 0, {
#                     'name':       self.name,
#                     'account_id': valuation_account.id,
#                     'debit':      0.0,
#                     'credit':     value,
#                 }),
#             ],
#         })
#         move.action_post()
#         self.register_move_id = move.id

#     def _create_asset_reverse_move(self):
#         """
#         Reversal on unregister:
#         Dr: Stock Valuation Account
#         Cr: Fixed Asset Account

#         BUG 5 FIX: guard journal_id
#         BUG 6 FIX: guard valuation account
#         """
#         self.ensure_one()

#         if not self.journal_id:
#             raise UserError(_(
#                 'Asset "%s" has no journal configured; cannot create reversal entry.'
#             ) % (self.code or self.name))

#         if not self.account_asset_id:
#             raise UserError(_(
#                 'Asset "%s" has no Fixed Asset Account; cannot create reversal entry.'
#             ) % (self.code or self.name))

#         valuation_account = self.product_id.categ_id.property_stock_valuation_account_id
#         if not valuation_account:
#             raise UserError(_(
#                 'Product category "%s" has no Stock Valuation Account; '
#                 'cannot create reversal entry.'
#             ) % self.product_id.categ_id.name)

#         value = self.original_value or self.purchase_price or 0.0

#         move = self.env['account.move'].create({
#             'journal_id': self.journal_id.id,
#             'date':       fields.Date.today(),
#             'ref':        f'Asset Unregister: {self.name}',
#             'line_ids': [
#                 (0, 0, {
#                     'name':       self.name,
#                     'account_id': valuation_account.id,
#                     'debit':      value,
#                     'credit':     0.0,
#                 }),
#                 (0, 0, {
#                     'name':       self.name,
#                     'account_id': self.account_asset_id.id,
#                     'debit':      0.0,
#                     'credit':     value,
#                 }),
#             ],
#         })
#         move.action_post()

#     # ─── Lifecycle action buttons ─────────────────────────────────────────────

#     def action_assign(self):
#         self.ensure_one()
#         if self.asset_state != 'available':
#             raise UserError(_('Only assets in "Available" state can be assigned.'))
#         return {
#             'type':      'ir.actions.act_window',
#             'name':      _('Assign Asset'),
#             'res_model': 'asset.assign.wizard',
#             'view_mode': 'form',
#             'target':    'new',
#             'context':   {'default_asset_id': self.id},
#         }

#     def action_return(self):
#         self.ensure_one()
#         if self.asset_state != 'assigned':
#             raise UserError(_('Only assigned assets can be returned.'))
#         return {
#             'type':      'ir.actions.act_window',
#             'name':      _('Return Asset'),
#             'res_model': 'asset.return.wizard',
#             'view_mode': 'form',
#             'target':    'new',
#             'context':   {'default_asset_id': self.id},
#         }

#     def action_scrap(self):
#         self.ensure_one()
#         if self.asset_state not in ('available', 'assigned'):
#             raise UserError(_('Only available or assigned assets can be scrapped.'))
#         old_state = self.asset_state
#         self.write({'asset_state': 'scrapped', 'current_employee_id': False})
#         self._log_history(
#             event_type='scrap',
#             old_state=old_state,
#             new_state='scrapped',
#             description=_('Asset scrapped by %s') % self.env.user.name,
#         )
#         return True

#     def action_dispose(self):
#         self.ensure_one()
#         if self.asset_state not in ('available', 'assigned'):
#             raise UserError(_('Only available or assigned assets can be disposed.'))
#         old_state = self.asset_state
#         self.write({'asset_state': 'disposed', 'current_employee_id': False})
#         self._log_history(
#             event_type='dispose',
#             old_state=old_state,
#             new_state='disposed',
#             description=_('Asset disposed by %s') % self.env.user.name,
#         )
#         return True

#     # ─── History logging ──────────────────────────────────────────────────────

#     def _log_history(self, event_type, old_state=None, new_state=None,
#                      employee_id=None, description=None, metadata=None):
#         self.env['asset.history'].sudo().create({
#             'asset_id':    self.id,
#             'event_type':  event_type,
#             'event_date':  fields.Datetime.now(),
#             'old_state':   old_state or '',
#             'new_state':   new_state or self.asset_state,
#             'employee_id': employee_id,
#             'user_id':     self.env.uid,
#             'description': description or _('State changed: %s → %s') % (old_state, new_state),
#             'metadata':    metadata or {},
#             'company_id':  self.company_id.id,
#         })

#     # ─── Available lot ids ────────────────────────────────────────────────────

#     @api.depends('product_id')
#     def _compute_available_lot_ids(self):
#         locked_lots = self.env['account.asset'].search([
#             ('lot_id',      '!=', False),
#             ('asset_state', '!=', 'draft'),
#             ('id',          'not in', self.ids),
#         ]).mapped('lot_id')

#         for rec in self:
#             domain = [('product_id', '=', rec.product_id.id)] if rec.product_id else []
#             product_lots = self.env['stock.lot'].search(domain)
#             rec.available_lot_ids = product_lots - locked_lots

#     # ─── Dashboard ───────────────────────────────────────────────────────────

#     def _cron_check_archived_employee_assets(self):
#         archived_employees = self.env['hr.employee'].with_context(active_test=False).search([
#             ('active', '=', False),
#         ])
#         if not archived_employees:
#             return

#         assets = self.search([
#             ('current_employee_id', 'in', archived_employees.ids),
#             ('asset_state',         '=',  'assigned'),
#         ])

#         activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
#         for asset in assets:
#             _logger.warning(
#                 'AMS: Asset %s is still assigned to archived employee %s',
#                 asset.code, asset.current_employee_id.name,
#             )
#             asset.activity_schedule(
#                 activity_type_id=activity_type.id if activity_type else False,
#                 summary=_('Asset return required — employee archived'),
#                 note=_(
#                     'Employee %s has been archived but still holds asset %s (%s). '
#                     'Please arrange return.'
#                 ) % (asset.current_employee_id.name, asset.code, asset.name),
#             )

#             if self.env.company.auto_return_on_employee_archive:
#                 assignment = self.env['asset.assignment'].search([
#                     ('asset_id',  '=', asset.id),
#                     ('is_active', '=', True),
#                 ], limit=1)
#                 if assignment:
#                     old_employee_id = asset.current_employee_id.id
#                     assignment.write({
#                         'is_active':           False,
#                         'return_date':         fields.Date.today(),
#                         'condition_on_return': 'fair',
#                     })
#                     asset.write({
#                         'asset_state':         'available',
#                         'current_employee_id': False,
#                     })
#                     asset._log_history(
#                         event_type='return',
#                         old_state='assigned',
#                         new_state='available',
#                         employee_id=old_employee_id,
#                         description=_('Auto-returned on employee archive by cron'),
#                     )

#     @api.model
#     def get_dashboard_data(self):
#         company_ids = self.env.companies.ids

#         assets = self.sudo().search([
#             ('lot_id',      '!=', False),
#             ('asset_state', 'not in', ['draft']),
#             ('company_id',  'in', company_ids),
#         ])

#         total             = len(assets)
#         available         = sum(1 for a in assets if a.asset_state == 'available')
#         assigned          = sum(1 for a in assets if a.asset_state == 'assigned')
#         scrapped_disposed = sum(1 for a in assets if a.asset_state in ('scrapped', 'disposed'))

#         active_assets     = assets.filtered(lambda a: a.asset_state in ('available', 'assigned'))
#         total_value       = sum(active_assets.mapped('original_value'))
#         net_book_value    = sum(active_assets.mapped('value_residual'))
#         total_depreciated = total_value - net_book_value

#         pending_depreciation = self.env['account.move'].sudo().search_count([
#             ('asset_id', 'in', active_assets.ids),
#             ('state',    '=', 'draft'),
#             ('date',     '<=', fields.Date.today()),
#         ])

#         category_data = {}
#         for asset in assets:
#             cat = asset.model_id.name or _('Uncategorised')
#             category_data[cat] = category_data.get(cat, 0) + 1

#         recent = self.env['asset.assignment'].sudo().search(
#             [('company_id', 'in', company_ids)],
#             order='assign_date desc',
#             limit=10,
#         )
#         recent_assignments = [
#             {
#                 'id':         a.id,
#                 'asset':      a.asset_id.name or '',
#                 'asset_code': a.asset_id.code or '',
#                 'employee':   a.employee_id.name or '',
#                 'date':       str(a.assign_date) if a.assign_date else '',
#                 'is_active':  a.is_active,
#             }
#             for a in recent
#         ]

#         return {
#             'total':                total,
#             'available':            available,
#             'assigned':             assigned,
#             'scrapped_disposed':    scrapped_disposed,
#             'total_value':          total_value,
#             'net_book_value':       net_book_value,
#             'total_depreciated':    total_depreciated,
#             'pending_depreciation': pending_depreciation,
#             'by_category': [
#                 {'category': k, 'count': v}
#                 for k, v in sorted(category_data.items(), key=lambda x: -x[1])
#             ],
#             'recent_assignments': recent_assignments,
#         }

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
    code = fields.Char(string='Asset Code', readonly=True, copy=False, index=True, tracking=True)
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
            ('draft',     'Draft'),
            ('available', 'Available'),
            ('assigned',  'Assigned'),
            ('returned',  'Returned'),
            ('scrapped',  'Scrapped'),
            ('disposed',  'Disposed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        index=True,
    )

    # ─── Dates & Financials ──────────────────────────────────────────────────

    purchase_date     = fields.Date(string='Purchase Date', tracking=True)
    registration_date = fields.Date(string='Registration Date', readonly=True)
    purchase_price    = fields.Monetary(
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

    location_id          = fields.Many2one('stock.location', string='Asset Location')
    original_location_id = fields.Many2one('stock.location', string='Original Location')
    current_employee_id  = fields.Many2one(
        'hr.employee',
        string='Assigned To',
        tracking=True,
        domain="[('company_id', '=', company_id)]",
    )
    
    assignment_ids = fields.One2many('asset.assignment', 'asset_id', string='Assignment History')
    history_ids    = fields.One2many('asset.history',    'asset_id', string='Lifecycle History')
    notes          = fields.Text(string='Notes')

    vendor_bill_line_id = fields.Many2one('account.move.line', string='Vendor Bill Line')
    register_move_id    = fields.Many2one('account.move',      string='Register Journal Entry')
    is_auto_created = fields.Boolean(
        string="Auto Created",
        default=False,
        copy=False
    )

    # ─── Constraints ─────────────────────────────────────────────────────────

    @api.constrains('lot_id')
    def _check_lot_unique(self):
        for rec in self:
            if rec.lot_id:
                existing = self.search([
                    ('lot_id', '=', rec.lot_id.id),
                    ('id',     '!=', rec.id),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        "A serial number can only be registered as one asset."
                    )

    # ─── Compute ─────────────────────────────────────────────────────────────

    @api.depends('product_id', 'lot_id')
    def _compute_name(self):
        for rec in self:
            if rec.product_id and rec.lot_id:
                rec.name = f'{rec.product_id.name} [{rec.lot_id.name}]'
            elif rec.product_id:
                rec.name = rec.product_id.name
            else:
                rec.name = rec.name or _('New Asset')

    @api.depends('product_id')
    def _compute_available_lot_ids(self):
        locked_lots = self.env['account.asset'].search([
            ('lot_id',      '!=', False),
            ('asset_state', '!=', 'draft'),
            ('id',          'not in', self.ids),
        ]).mapped('lot_id')
        for rec in self:
            domain = [('product_id', '=', rec.product_id.id)] if rec.product_id else []
            product_lots = self.env['stock.lot'].search(domain)
            rec.available_lot_ids = product_lots - locked_lots

    # ─── ORM ─────────────────────────────────────────────────────────────────
    # code = fields.Char(string='Asset Code', readonly=True, copy=False, index=True, tracking=True, store=True)
    @api.model_create_multi
    def create(self, vals_list):
        seq_model = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('code') and vals.get('lot_id'):
                code = seq_model.next_by_code('account.asset.code')
                if not code:
                    raise ValidationError(
                        "Sequence 'account.asset.code' is not configured."
                    )
                vals['code'] = code
        return super().create(vals_list)

    # ─────────────────────────────────────────────────────────────────────────
    # action_register
    # ─────────────────────────────────────────────────────────────────────────

    # def action_register(self):
    #     """
    #     Register each asset in self (model-level / auto-create path).

    #     Stock on hand
    #     ─────────────
    #     Source      : quant with usage='internal' — this is where real on-hand
    #                   stock lives.  Filtering to 'internal' prevents accidental
    #                   reads from scrap, virtual, or transit locations.

    #     Destination : asset_location with usage='inventory' (virtual).
    #                   Moving to an inventory-type virtual location immediately
    #                   removes the serial from all stock-on-hand reports.

    #     Unregister reverses exactly: virtual → original internal location,
    #     restoring the on-hand count to what it was before registration.

    #     Accounting
    #     ──────────
    #     Dr  Fixed Asset Account     (account_asset_id)
    #     Cr  Stock Valuation Account (product categ property)
    #     """
    #     for rec in self:
    #         # ── 1. Guard ──────────────────────────────────────────────────────
    #         if rec.asset_state != 'draft':
    #             raise UserError(_("Only draft assets can be registered"))
    #         if not rec.product_id or not rec.lot_id:
    #             raise UserError(_("Product and Serial Number are required"))

    #         # ── 2. Source: find the serial in real (internal) stock ───────────
    #         #
    #         # Restrict to usage='internal' so we never accidentally consume
    #         # from a scrap or virtual location that doesn't represent real stock.
    #         source_quant = self.env['stock.quant'].sudo().search([
    #             ('product_id',        '=', rec.product_id.id),
    #             ('lot_id',            '=', rec.lot_id.id),
    #             ('quantity',          '>',  0),
    #             ('location_id.usage', '=', 'internal'),
    #         ], limit=1)

    #         if not source_quant:
    #             raise UserError(_(
    #                 'Serial number "%s" is not available in any internal stock '
    #                 'location.\nReceive it into inventory before registering it '
    #                 'as an asset.'
    #             ) % rec.lot_id.name)

    #         source_location = source_quant.location_id
    #         # Save the exact source location — unregister will move back here.
    #         rec.original_location_id = source_location

    #         # ── 3. Destination: asset virtual location ────────────────────────
    #         #
    #         # This location MUST have usage='inventory'.  The domain on
    #         # res.company.asset_location_id enforces this in the Settings UI.
    #         # We also check at runtime so a mis-configured server raises a
    #         # clear error instead of silently leaving stock on hand unchanged.
    #         asset_location = (
    #             self.env.company.asset_location_id
    #             or self.env.ref(
    #                 'asset_management_bdcalling.asset_stock_location',
    #                 raise_if_not_found=False,
    #             )
    #         )
    #         if not asset_location:
    #             raise UserError(_(
    #                 'No Default Asset Location configured.\n'
    #                 'Go to Asset Management → Configuration → Settings and set '
    #                 'the "Default Asset Location" to a Virtual/Inventory location.'
    #             ))
    #         if asset_location.usage != 'inventory':
    #             raise UserError(_(
    #                 'Asset Location "%s" has usage "%s".\n'
    #                 'It must be "Virtual Locations / Inventory" (usage=inventory) '
    #                 'so that registering an asset decreases the product\'s stock '
    #                 'on hand.  Please update the location or pick a different one '
    #                 'in Asset Management → Configuration → Settings.'
    #             ) % (asset_location.complete_name, asset_location.usage))

    #         # ── 4. Stock move: internal → virtual ─────────────────────────────
    #         #    Effect: decreases product stock on hand by 1 unit
    #         # move = self.env['stock.move'].create({
    #         #     'product_id':          rec.product_id.id,
    #         #     'product_uom_qty':     1,
    #         #     'product_uom':         rec.product_id.uom_id.id,
    #         #     'location_id':         source_location.id,
    #         #     'location_dest_id':    asset_location.id,
    #         #     'description_picking': f'Asset Register: {rec.name}',
    #         #     'company_id':          rec.company_id.id,
    #         # })
    #         # move._action_confirm()
    #         # move._action_assign()
    #         # self.env['stock.move.line'].create({
    #         #     'move_id':          move.id,
    #         #     'product_id':       rec.product_id.id,
    #         #     'qty_done':         1,
    #         #     'location_id':      source_location.id,
    #         #     'location_dest_id': asset_location.id,
    #         #     'lot_id':           rec.lot_id.id,
    #         # })
    #         # move._action_done()
    #         # rec.location_id = asset_location
    #         move = self.env['stock.move'].create({
    #             'product_id':          rec.product_id.id,
    #             'product_uom_qty':     1,
    #             'product_uom':         rec.product_id.uom_id.id,
    #             'location_id':         source_location.id,
    #             'location_dest_id':    asset_location.id,
    #             'description_picking': f'Asset Register: {rec.name}',
    #             'company_id':          rec.company_id.id,
    #         })
    #         move._action_confirm()
    #         move._action_assign()
    #         # Odoo 17+: the done quantity field is 'quantity' (not 'qty_done').
    #         # _action_assign() may already create move lines; update them rather
    #         # than creating a duplicate line.
    #         if move.move_line_ids:
    #             move.move_line_ids.write({
    #                 'quantity': 1,
    #                 'lot_id':   rec.lot_id.id,
    #             })
    #         else:
    #             self.env['stock.move.line'].create({
    #                 'move_id':          move.id,
    #                 'product_id':       rec.product_id.id,
    #                 'quantity':         1,           # ← 'quantity', not 'qty_done'
    #                 'location_id':      source_location.id,
    #                 'location_dest_id': asset_location.id,
    #                 'lot_id':           rec.lot_id.id,
    #             })
    #         # Flush all pending ORM writes before _action_done so stock_account's
    #         # _set_value() can read standard_price without a cursor-state error.
    #         self.env.flush_all()
    #         move._action_done()
    #         rec.location_id = asset_location

    #         # ── 5. Accounting journal entry ───────────────────────────────────
    #         rec._create_asset_account_move()

    #         # ── 6. Depreciation schedule (validate) ───────────────────────────
    #         if (rec.account_asset_id
    #                 and rec.account_depreciation_id
    #                 and rec.account_depreciation_expense_id
    #                 and rec.journal_id
    #                 and rec.method
    #                 and rec.method_number):
    #             try:
    #                 rec.validate()
    #             except UserError:
    #                 raise
    #             except Exception as exc:
    #                 _logger.error(
    #                     'AMS: validate() failed for asset %s: %s', rec.code, exc
    #                 )
    #                 raise UserError(_(
    #                     'Depreciation schedule generation failed for "%s".\n%s\n\n'
    #                     'Verify the accounting configuration on the asset category.'
    #                 ) % (rec.name, exc))
    #         else:
    #             _logger.warning(
    #                 'AMS: asset %s is missing accounting config; '
    #                 'depreciation schedule was NOT generated.',
    #                 rec.code,
    #             )

    #         # ── 7. Finalise ───────────────────────────────────────────────────
    #         rec.write({
    #             'asset_state':       'available',
    #             'registration_date': fields.Date.today(),
    #         })
    #         rec._log_history(
    #             event_type='register',
    #             old_state='draft',
    #             new_state='available',
    #             description=_('Asset registered by %s') % self.env.user.name,
    #             metadata={
    #                 'source_location': source_location.complete_name,
    #                 'asset_location':  asset_location.complete_name,
    #             },
    #         )

    def action_register(self):
        for rec in self:
            # ── 1. Guard ──────────────────────────────────────────────────────
            if rec.asset_state != 'draft':
                raise UserError(_("Only draft assets can be registered"))
            if not rec.product_id or not rec.lot_id:
                raise UserError(_("Product and Serial Number are required"))

            # ── 2. Source: find serial in real (internal) stock ───────────────
            source_quant = self.env['stock.quant'].sudo().search([
                ('product_id',        '=', rec.product_id.id),
                ('lot_id',            '=', rec.lot_id.id),
                ('quantity',          '>',  0),
                ('location_id.usage', '=', 'internal'),
            ], limit=1)

            if not source_quant:
                raise UserError(_(
                    'Serial number "%s" is not available in any internal stock '
                    'location.\nReceive it into inventory before registering.'
                ) % rec.lot_id.name)

            source_location = source_quant.location_id
            rec.original_location_id = source_location

            # ── 3. Destination: asset virtual location ────────────────────────
            asset_location = (
                self.env.company.asset_location_id
                or self.env.ref(
                    'asset_management_bdcalling.asset_stock_location',
                    raise_if_not_found=False,
                )
            )
            if not asset_location:
                raise UserError(_(
                    'No Default Asset Location configured.\n'
                    'Go to Asset Management → Configuration → Settings.'
                ))
            if asset_location.usage != 'inventory':
                raise UserError(_(
                    'Asset Location "%s" must have usage "inventory" (Virtual/Inventory).'
                ) % asset_location.complete_name)

            # ── 4. Stock move ─────────────────────────────────────────────────
            # FIX 1: flush all pending ORM writes BEFORE _action_done() so that
            # stock_account's internal savepoint(flush=True) finds nothing dirty
            # to flush — eliminating the implicit-flush failure that corrupts the
            # psycopg2 cursor state.
            self.env.flush_all()

            move = self.env['stock.move'].create({
                'product_id':          rec.product_id.id,
                'product_uom_qty':     1,
                'product_uom':         rec.product_id.uom_id.id,
                'location_id':         source_location.id,
                'location_dest_id':    asset_location.id,
                'description_picking': f'Asset Register: {rec.name}',
                'company_id':          rec.company_id.id,
            })
            move._action_confirm()
            move._action_assign()

            # FIX 2: In Odoo 17+, the done-quantity field is 'quantity' (not
            # 'qty_done'). Also, _action_assign() may already create the move
            # line — update it instead of creating a duplicate.
            if move.move_line_ids:
                move.move_line_ids.write({
                    'quantity': 1,
                    'lot_id':   rec.lot_id.id,
                })
            else:
                self.env['stock.move.line'].create({
                    'move_id':          move.id,
                    'product_id':       rec.product_id.id,
                    'quantity':         1,          # ← 'quantity', NOT 'qty_done'
                    'location_id':      source_location.id,
                    'location_dest_id': asset_location.id,
                    'lot_id':           rec.lot_id.id,
                })

            # FIX 3: flush again right before _action_done() so no pending
            # writes remain when stock_account's savepoint(flush=True) fires.
            self.env.flush_all()
            move._action_done()

            # FIX 4: invalidate ORM cache after stock_account's internal
            # savepoints complete — this resets any stale cursor state so
            # subsequent operations (account.move creation, validate()) start
            # with a clean connection to PostgreSQL.
            self.env.invalidate_all()

            rec.location_id = asset_location

            # ── 5. Accounting journal entry ───────────────────────────────────
            rec._create_asset_account_move()

            # ── 6. Depreciation schedule ──────────────────────────────────────
            # FIX 5: flush before validate() for the same reason — validate()
            # calls _compute_depreciation_board() which creates many account.move
            # records, each triggering savepoint(flush=True) internally.
            self.env.flush_all()

            if (rec.account_asset_id
                    and rec.account_depreciation_id
                    and rec.account_depreciation_expense_id
                    and rec.journal_id
                    and rec.method
                    and rec.method_number):
                try:
                    rec.validate()
                except UserError:
                    raise
                except Exception as exc:
                    _logger.error(
                        'AMS: validate() failed for asset %s: %s', rec.code, exc
                    )
                    raise UserError(_(
                        'Depreciation schedule generation failed for "%s".\n%s\n\n'
                        'Verify the accounting configuration on the asset category.'
                    ) % (rec.name, exc))
            else:
                _logger.warning(
                    'AMS: asset %s missing accounting config; '
                    'depreciation schedule NOT generated.', rec.code,
                )

            # ── 7. Finalise ───────────────────────────────────────────────────
            rec.write({
                'asset_state':       'available',
                'registration_date': fields.Date.today(),
            })
            rec._log_history(
                event_type='register',
                old_state='draft',
                new_state='available',
                description=_('Asset registered by %s') % self.env.user.name,
                metadata={
                    'source_location': source_location.complete_name,
                    'asset_location':  asset_location.complete_name,
                },
            )

    # ─────────────────────────────────────────────────────────────────────────
    # action_unregister
    # ─────────────────────────────────────────────────────────────────────────

    # def action_unregister(self):
    #     """
    #     Reverse a registration.

    #     Stock move: wherever the serial currently is (the virtual asset location)
    #                 → original_location_id (the internal location saved on register).
    #     Effect: increases product stock on hand by 1 unit.
    #     """
    #     self.ensure_one()

    #     if self.asset_state != 'available':
    #         raise UserError(_("Only available assets can be unregistered"))
    #     if not self.product_id or not self.lot_id:
    #         raise UserError(_("Product and Serial Number required"))

    #     # ── Locate the serial (expected to be in the virtual asset location) ──
    #     source_quant = self.env['stock.quant'].sudo().search([
    #         ('product_id', '=', self.product_id.id),
    #         ('lot_id',     '=', self.lot_id.id),
    #         ('quantity',   '>',  0),
    #     ], limit=1)

    #     if not source_quant:
    #         raise UserError(_(
    #             'Serial number "%s" could not be found in any stock location.\n'
    #             'It may have been moved or deleted manually.'
    #         ) % self.lot_id.name)

    #     source_location = source_quant.location_id

    #     # ── Restore to the original internal location ─────────────────────────
    #     # original_location_id is always an internal location set during register.
    #     destination_location = (
    #         self.original_location_id
    #         or self.env.ref('stock.stock_location_stock')
    #     )

    #     # ── Stock move: virtual → internal ────────────────────────────────────
    #     #    Effect: increases product stock on hand by 1 unit
    #     # move = self.env['stock.move'].create({
    #     #     'product_id':          self.product_id.id,
    #     #     'product_uom_qty':     1,
    #     #     'product_uom':         self.product_id.uom_id.id,
    #     #     'location_id':         source_location.id,
    #     #     'location_dest_id':    destination_location.id,
    #     #     'description_picking': f'Asset Unregister: {self.name}',
    #     #     'company_id':          self.company_id.id,
    #     # })
    #     # move._action_confirm()
    #     # move._action_assign()
    #     # self.env['stock.move.line'].create({
    #     #     'move_id':          move.id,
    #     #     'product_id':       self.product_id.id,
    #     #     'qty_done':         1,
    #     #     'location_id':      source_location.id,
    #     #     'location_dest_id': destination_location.id,
    #     #     'lot_id':           self.lot_id.id,
    #     # })
    #     # move._action_done()
    #     move = self.env['stock.move'].create({
    #         'product_id':          self.product_id.id,
    #         'product_uom_qty':     1,
    #         'product_uom':         self.product_id.uom_id.id,
    #         'location_id':         source_location.id,
    #         'location_dest_id':    destination_location.id,
    #         'description_picking': f'Asset Unregister: {self.name}',
    #         'company_id':          self.company_id.id,
    #     })
    #     move._action_confirm()
    #     move._action_assign()
    #     if move.move_line_ids:
    #         move.move_line_ids.write({
    #             'quantity': 1,
    #             'lot_id':   self.lot_id.id,
    #         })
    #     else:
    #         self.env['stock.move.line'].create({
    #             'move_id':          move.id,
    #             'product_id':       self.product_id.id,
    #             'quantity':         1,           # ← 'quantity', not 'qty_done'
    #             'location_id':      source_location.id,
    #             'location_dest_id': destination_location.id,
    #             'lot_id':           self.lot_id.id,
    #         })
    #     self.env.flush_all()
    #     move._action_done()

    #     # ── Reverse journal entry ─────────────────────────────────────────────
    #     self._create_asset_reverse_move()

    #     old_state = self.asset_state
    #     self.write({
    #         'asset_state':          'draft',
    #         'registration_date':    False,
    #         'location_id':          False,
    #         'original_location_id': False,
    #     })
    #     self._log_history(
    #         event_type='unregister',
    #         old_state=old_state,
    #         new_state='draft',
    #         description=_('Asset unregistered by %s') % self.env.user.name,
    #         metadata={'restored_to': destination_location.complete_name},
    #     )

    def action_unregister(self):
        self.ensure_one()

        if self.asset_state != 'available':
            raise UserError(_("Only available assets can be unregistered"))
        if not self.product_id or not self.lot_id:
            raise UserError(_("Product and Serial Number required"))

        source_quant = self.env['stock.quant'].sudo().search([
            ('product_id', '=', self.product_id.id),
            ('lot_id',     '=', self.lot_id.id),
            ('quantity',   '>',  0),
        ], limit=1)

        if not source_quant:
            raise UserError(_(
                'Serial number "%s" could not be found in any stock location.'
            ) % self.lot_id.name)

        source_location      = source_quant.location_id
        destination_location = (
            self.original_location_id
            or self.env.ref('stock.stock_location_stock')
        )

        self.env.flush_all()   # ← flush before stock operations

        move = self.env['stock.move'].create({
            'product_id':          self.product_id.id,
            'product_uom_qty':     1,
            'product_uom':         self.product_id.uom_id.id,
            'location_id':         source_location.id,
            'location_dest_id':    destination_location.id,
            'description_picking': f'Asset Unregister: {self.name}',
            'company_id':          self.company_id.id,
        })
        move._action_confirm()
        move._action_assign()

        # FIX: same pattern — update existing lines, use 'quantity' not 'qty_done'
        if move.move_line_ids:
            move.move_line_ids.write({
                'quantity': 1,
                'lot_id':   self.lot_id.id,
            })
        else:
            self.env['stock.move.line'].create({
                'move_id':          move.id,
                'product_id':       self.product_id.id,
                'quantity':         1,          # ← 'quantity', NOT 'qty_done'
                'location_id':      source_location.id,
                'location_dest_id': destination_location.id,
                'lot_id':           self.lot_id.id,
            })

        self.env.flush_all()
        move._action_done()
        self.env.invalidate_all()   # ← reset cursor state after stock_account

        self._create_asset_reverse_move()

        old_state = self.asset_state
        self.write({
            'asset_state':          'draft',
            'registration_date':    False,
            'location_id':          False,
            'original_location_id': False,
        })
        self._log_history(
            event_type='unregister',
            old_state=old_state,
            new_state='draft',
            description=_('Asset unregistered by %s') % self.env.user.name,
            metadata={'restored_to': destination_location.complete_name},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # action_auto_create_from_product_serials
    # ─────────────────────────────────────────────────────────────────────────

    def action_auto_create_from_product_serials(self):
        """
        Create one draft account.asset per unregistered serial of self.product_id,
        then immediately register each one (decreasing stock on hand per serial).
        action_register() is called on the individual asset, not on the growing
        recordset.
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

        taken_lot_ids = self.env['account.asset'].search([
            ('lot_id',     '!=', False),
            ('product_id', '=',  self.product_id.id),
            ('id',         '!=', self.id),
        ]).mapped('lot_id').ids

        free_lots = all_lots.filtered(lambda l: l.id not in taken_lot_ids)
        if not free_lots:
            raise UserError(_(
                'All serial numbers for "%s" already have asset records.'
            ) % self.product_id.name)

        bill_line = self.vendor_bill_line_id
        if bill_line:
            unit_price = bill_line.price_subtotal / (bill_line.quantity or 1)
        else:
            unit_price = self.original_value or self.purchase_price or 0.0

        created = self.env['account.asset']

        for lot in free_lots:
            asset = self.env['account.asset'].create({
                'name':        f'{self.product_id.name} [{lot.name}]',
                'product_id':  self.product_id.id,
                'lot_id':      lot.id,
                'company_id':  self.company_id.id,
                'asset_state': 'draft',
                'original_value':                  unit_price,
                'purchase_price':                  unit_price,
                'vendor_bill_line_id':              bill_line.id if bill_line else False,
                'model_id':                        self.model_id.id if self.model_id else False,
                'acquisition_date':                self.acquisition_date or fields.Date.today(),
                'account_asset_id':                self.account_asset_id.id if self.account_asset_id else False,
                'account_depreciation_id':         self.account_depreciation_id.id if self.account_depreciation_id else False,
                'account_depreciation_expense_id': self.account_depreciation_expense_id.id if self.account_depreciation_expense_id else False,
                'journal_id':                      self.journal_id.id if self.journal_id else False,
                'method':                          self.method        or False,
                'method_number':                   self.method_number or 0,
                'method_period':                   self.method_period or '1',
                'is_auto_created': True,
            })
            # Register THIS asset only — not the accumulating recordset
            try:
                asset.action_register()
                created |= asset
            except UserError:
                raise

        _logger.info(
            'AMS: auto-created and registered %d assets for product %s',
            len(created), self.product_id.name,
        )

        if len(created) == 1:
            return {
                'type':      'ir.actions.act_window',
                'name':      _('Asset'),
                'res_model': 'account.asset',
                'res_id':    created.id,
                'view_mode': 'form',
                'target':    'current',
            }
        return {
            'type':      'ir.actions.act_window',
            'name':      _('%d Assets Created') % len(created),
            'res_model': 'account.asset',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', created.ids)],
            'target':    'current',
        }

    # ─── Journal entry helpers ────────────────────────────────────────────────

    def _create_asset_account_move(self):
        """
        Dr  Fixed Asset Account       (account_asset_id)
        Cr  Stock Valuation Account   (product categ property)
        """
        self.ensure_one()

        if not self.journal_id:
            raise UserError(_(
                'Asset "%s" has no journal configured. '
                'Set it on the asset category before registering.'
            ) % (self.code or self.name))
        
        if not self.account_asset_id:
            raise UserError(_(
                'Asset "%s" has no Fixed Asset Account configured.'
            ) % (self.code or self.name))

        valuation_account = self.product_id.categ_id.property_stock_valuation_account_id
        if not valuation_account:
            raise UserError(_(
                'Product category "%s" has no Stock Valuation Account. '
                'Go to Inventory → Configuration → Product Categories and set it.'
            ) % self.product_id.categ_id.name)

        value = self.original_value or self.purchase_price or 0.0
        if not value:
            _logger.warning(
                'AMS: asset %s has zero value; journal entry will be zero-amount.',
                self.code,
            )

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date':       fields.Date.today(),
            'ref':        f'Asset Register: {self.name}',
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'line_ids': [
                (0, 0, {
                    'name':       self.name,
                    'account_id': self.account_asset_id.id,
                    'debit':      value,
                    'credit':     0.0,
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                }),
                (0, 0, {
                    'name':       self.name,
                    'account_id': valuation_account.id,
                    'debit':      0.0,
                    'credit':     value,
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                }),
            ],
        })
        move.action_post()
        self.register_move_id = move.id

    def _create_asset_reverse_move(self):
        """
        Dr  Stock Valuation Account   (product categ property)
        Cr  Fixed Asset Account       (account_asset_id)
        """
        self.ensure_one()

        if not self.journal_id:
            raise UserError(_(
                'Asset "%s" has no journal configured; cannot create reversal entry.'
            ) % (self.code or self.name))
        if not self.account_asset_id:
            raise UserError(_(
                'Asset "%s" has no Fixed Asset Account; cannot create reversal entry.'
            ) % (self.code or self.name))

        valuation_account = self.product_id.categ_id.property_stock_valuation_account_id
        if not valuation_account:
            raise UserError(_(
                'Product category "%s" has no Stock Valuation Account; '
                'cannot create reversal entry.'
            ) % self.product_id.categ_id.name)

        value = self.original_value or self.purchase_price or 0.0

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date':       fields.Date.today(),
            'ref':        f'Asset Unregister: {self.name}',
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'line_ids': [
                (0, 0, {
                    'name':       self.name,
                    'account_id': valuation_account.id,
                    'debit':      value,
                    'credit':     0.0,
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                }),
                (0, 0, {
                    'name':       self.name,
                    'account_id': self.account_asset_id.id,
                    'debit':      0.0,
                    'credit':     value,
                    'currency_id': self.currency_id.id,
                    'company_id': self.company_id.id,
                }),
            ],
        })
        move.action_post()

    # ─── Lifecycle buttons ────────────────────────────────────────────────────

    def action_assign(self):
        self.ensure_one()
        if self.asset_state != 'available':
            raise UserError(_('Only assets in "Available" state can be assigned.'))
        return {
            'type': 'ir.actions.act_window', 'name': _('Assign Asset'),
            'res_model': 'asset.assign.wizard', 'view_mode': 'form',
            'target': 'new', 'context': {'default_asset_id': self.id},
        }

    def action_return(self):
        self.ensure_one()
        if self.asset_state != 'assigned':
            raise UserError(_('Only assigned assets can be returned.'))
        return {
            'type': 'ir.actions.act_window', 'name': _('Return Asset'),
            'res_model': 'asset.return.wizard', 'view_mode': 'form',
            'target': 'new', 'context': {'default_asset_id': self.id},
        }

    def action_scrap(self):
        self.ensure_one()
        if self.asset_state not in ('available', 'assigned'):
            raise UserError(_('Only available or assigned assets can be scrapped.'))
        old_state = self.asset_state
        self.write({'asset_state': 'scrapped', 'current_employee_id': False})
        self._log_history(
            event_type='scrap', old_state=old_state, new_state='scrapped',
            description=_('Asset scrapped by %s') % self.env.user.name,
        )
        return True

    def action_dispose(self):
        self.ensure_one()
        if self.asset_state not in ('available', 'assigned'):
            raise UserError(_('Only available or assigned assets can be disposed.'))
        old_state = self.asset_state
        self.write({'asset_state': 'disposed', 'current_employee_id': False})
        self._log_history(
            event_type='dispose', old_state=old_state, new_state='disposed',
            description=_('Asset disposed by %s') % self.env.user.name,
        )
        return True

    # ─── History ─────────────────────────────────────────────────────────────

    def _log_history(self, event_type, old_state=None, new_state=None,
                     employee_id=None, description=None, metadata=None):
        self.env['asset.history'].sudo().create({
            'asset_id':    self.id,
            'event_type':  event_type,
            'event_date':  fields.Datetime.now(),
            'old_state':   old_state or '',
            'new_state':   new_state or self.asset_state,
            'employee_id': employee_id,
            'user_id':     self.env.uid,
            'description': description or _('State changed: %s → %s') % (old_state, new_state),
            'metadata':    metadata or {},
            'company_id':  self.company_id.id,
        })

    @api.depends('product_id')
    def _compute_available_lot_ids(self):
        locked_lots = self.env['account.asset'].search([
            ('lot_id',      '!=', False),
            ('asset_state', '!=', 'draft'),
            ('id',          'not in', self.ids),
        ]).mapped('lot_id')
        for rec in self:
            domain = [('product_id', '=', rec.product_id.id)] if rec.product_id else []
            product_lots = self.env['stock.lot'].search(domain)
            rec.available_lot_ids = product_lots - locked_lots

    # ─── Cron ────────────────────────────────────────────────────────────────

    def _cron_check_archived_employee_assets(self):
        archived_employees = self.env['hr.employee'].with_context(
            active_test=False
        ).search([('active', '=', False)])
        if not archived_employees:
            return
        assets = self.search([
            ('current_employee_id', 'in', archived_employees.ids),
            ('asset_state',         '=',  'assigned'),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for asset in assets:
            _logger.warning(
                'AMS: Asset %s still assigned to archived employee %s',
                asset.code, asset.current_employee_id.name,
            )
            asset.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('Asset return required — employee archived'),
                note=_(
                    'Employee %s has been archived but still holds asset %s (%s). '
                    'Please arrange return.'
                ) % (asset.current_employee_id.name, asset.code, asset.name),
            )
            if self.env.company.auto_return_on_employee_archive:
                assignment = self.env['asset.assignment'].search([
                    ('asset_id',  '=', asset.id),
                    ('is_active', '=', True),
                ], limit=1)
                if assignment:
                    old_employee_id = asset.current_employee_id.id
                    assignment.write({
                        'is_active':           False,
                        'return_date':         fields.Date.today(),
                        'condition_on_return': 'fair',
                    })
                    asset.write({
                        'asset_state':         'available',
                        'current_employee_id': False,
                    })
                    asset._log_history(
                        event_type='return',
                        old_state='assigned',
                        new_state='available',
                        employee_id=old_employee_id,
                        description=_('Auto-returned on employee archive by cron'),
                    )

    # ─── Dashboard ───────────────────────────────────────────────────────────

    @api.model
    def get_dashboard_data(self):
        company_ids = self.env.companies.ids
        assets = self.sudo().search([
            ('lot_id',      '!=', False),
            ('asset_state', 'not in', ['draft']),
            ('company_id',  'in', company_ids),
        ])
        total             = len(assets)
        available         = sum(1 for a in assets if a.asset_state == 'available')
        assigned          = sum(1 for a in assets if a.asset_state == 'assigned')
        scrapped_disposed = sum(1 for a in assets if a.asset_state in ('scrapped', 'disposed'))
        active_assets     = assets.filtered(lambda a: a.asset_state in ('available', 'assigned'))
        total_value       = sum(active_assets.mapped('original_value'))
        net_book_value    = sum(active_assets.mapped('value_residual'))
        total_depreciated = total_value - net_book_value
        pending_depreciation = self.env['account.move'].sudo().search_count([
            ('asset_id', 'in', active_assets.ids),
            ('state',    '=', 'draft'),
            ('date',     '<=', fields.Date.today()),
        ])
        category_data = {}
        for asset in assets:
            cat = asset.model_id.name or _('Uncategorised')
            category_data[cat] = category_data.get(cat, 0) + 1
        recent = self.env['asset.assignment'].sudo().search(
            [('company_id', 'in', company_ids)],
            order='assign_date desc',
            limit=10,
        )
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
                for k, v in sorted(category_data.items(), key=lambda x: -x[1])
            ],
            'recent_assignments': [
                {
                    'id':         a.id,
                    'asset':      a.asset_id.name or '',
                    'asset_code': a.asset_id.code or '',
                    'employee':   a.employee_id.name or '',
                    'date':       str(a.assign_date) if a.assign_date else '',
                    'is_active':  a.is_active,
                }
                for a in recent
            ],
        }