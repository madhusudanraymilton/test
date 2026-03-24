# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _
# from odoo.exceptions import UserError
# import logging

# _logger = logging.getLogger(__name__)


# class AssetRegisterWizard(models.TransientModel):
#     _name = 'asset.register.wizard'
#     _description = 'Asset Registration Wizard'

#     # Pre-filled via context (default_asset_id) when opened from asset form.
#     asset_id = fields.Many2one(
#         'account.asset',
#         string='Asset Record',
#         readonly=True,
#     )

#     # ── Serial / Product ──────────────────────────────────────────────────────
#     lot_id = fields.Many2one(
#         'stock.lot',
#         string='Serial Number',
#         required=True,
#     )
#     product_id = fields.Many2one(
#         'product.product',
#         string='Product',
#         compute='_compute_from_lot',
#         store=True,
#         readonly=False,
#     )

#     # ── Auto-filled from Purchase Order via lot ───────────────────────────────
#     purchase_price = fields.Monetary(
#         string='Purchase Price',
#         currency_field='currency_id',
#         required=True,
#         help='Auto-filled from the Purchase Order line that received this serial number.',
#     )
#     purchase_date = fields.Date(
#         string='Purchase Date',
#         help='Auto-filled from the Purchase Order confirmation date.',
#     )
#     purchase_order_id = fields.Many2one(
#         'purchase.order',
#         string='Source Purchase Order',
#         readonly=True,
#         help='The purchase order from which this serial number was received.',
#     )
#     purchase_order_line_id = fields.Many2one(
#         'purchase.order.line',
#         string='Purchase Order Line',
#         readonly=True,
#     )

#     # ── Classification & Location ─────────────────────────────────────────────
#     category_id = fields.Many2one(
#         'account.asset',
#         string='Asset Category',
#         required=True,
#         domain="[('state', '=', 'model'), ('company_id', 'in', [company_id, False])]",
#     )
#     source_location_id = fields.Many2one(
#         'stock.location',
#         string='Source Location',
#         required=True,
#         domain="[('usage', 'in', ['internal', 'transit'])]",
#         default=lambda self: self.env.ref(
#             'stock.stock_location_stock', raise_if_not_found=False
#         ),
#     )

#     # ── Currency & Misc ───────────────────────────────────────────────────────
#     currency_id = fields.Many2one(
#         'res.currency',
#         default=lambda self: self.env.company.currency_id,
#     )
#     notes = fields.Text(string='Notes')
#     company_id = fields.Many2one(
#         'res.company',
#         default=lambda self: self.env.company,
#     )

#     # Lots already locked by a registered (non-draft) AMS asset.
#     registered_lot_ids = fields.Many2many(
#         'stock.lot',
#         compute='_compute_registered_lot_ids',
#         string='Already Registered Serials',
#     )

#     # =========================================================================
#     # COMPUTE
#     # =========================================================================

#     @api.depends_context('uid')
#     def _compute_registered_lot_ids(self):
#         locked = self.env['account.asset'].search([
#             ('lot_id',      '!=', False),
#             ('asset_state', 'not in', ['draft']),
#         ]).mapped('lot_id')
#         for rec in self:
#             rec.registered_lot_ids = locked

#     @api.depends('lot_id')
#     def _compute_from_lot(self):
#         """
#         When a serial/lot is selected, auto-fill:
#           - product_id         from lot.product_id
#           - purchase_price     from the PO line unit price (currency-converted)
#           - purchase_date      from PO confirmation date (date_approve)
#           - purchase_order_id  for display/traceability
#           - purchase_order_line_id for reference

#         Lookup path (Odoo 19):
#           stock.lot
#             → stock.move.line  (lot_id, state='done')
#               → stock.move     (move_id, purchase_line_id != False)
#                 → purchase.order.line  (purchase_line_id)
#                   → purchase.order     (order_id)

#         We take the most recent done receipt for the lot so that if a serial
#         was returned and re-purchased, the latest price is used.
#         """
#         for rec in self:
#             if not rec.lot_id:
#                 rec.product_id           = False
#                 rec.purchase_price       = 0.0
#                 rec.purchase_date        = False
#                 rec.purchase_order_id    = False
#                 rec.purchase_order_line_id = False
#                 continue

#             # Always set product from lot
#             rec.product_id = rec.lot_id.product_id

#             # ── Find the purchase move line for this lot ───────────────────────
#             # Filter: move must be done, must link to a PO line, and must be a
#             # receipt (location_dest_id is an internal/customer/transit location,
#             # i.e. not a supplier location — meaning stock came IN).
#             move_lines = self.env['stock.move.line'].search([
#                 ('lot_id',         '=', rec.lot_id.id),
#                 ('state',          '=', 'done'),
#                 ('move_id.purchase_line_id', '!=', False),
#             ], order='date desc', limit=1)

#             if not move_lines:
#                 # No PO receipt found — leave price/date for manual input
#                 rec.purchase_price       = 0.0
#                 rec.purchase_date        = False
#                 rec.purchase_order_id    = False
#                 rec.purchase_order_line_id = False
#                 continue

#             po_line = move_lines.move_id.purchase_line_id
#             po      = po_line.order_id

#             # ── Price: convert from PO currency to company currency if needed ──
#             price_unit = po_line.price_unit
#             if po.currency_id and po.currency_id != rec.currency_id:
#                 price_unit = po.currency_id._convert(
#                     price_unit,
#                     rec.currency_id,
#                     rec.company_id,
#                     po.date_approve or fields.Date.today(),
#                 )

#             rec.purchase_price         = price_unit
#             rec.purchase_date          = po.date_approve or po.date_order
#             rec.purchase_order_id      = po
#             rec.purchase_order_line_id = po_line

#     # =========================================================================
#     # ACTION
#     # =========================================================================

#     def action_register(self):
#         self.ensure_one()

#         # ── 0. Resolve which AMS asset we are registering ─────────────────────
#         asset = self.asset_id
#         if not asset:
#             asset = self.env['account.asset'].search([
#                 ('lot_id',      '=', self.lot_id.id),
#                 ('asset_state', '=', 'draft'),
#             ], limit=1)

#         # ── 1. Inventory check ────────────────────────────────────────────────
#         quant = self.env['stock.quant'].search([
#             ('lot_id',      '=', self.lot_id.id),
#             ('location_id', '=', self.source_location_id.id),
#         ], limit=1)
#         if not quant or quant.quantity < 1:
#             raise UserError(_(
#                 'Serial number "%s" is not available (qty < 1) in location "%s".'
#             ) % (self.lot_id.name, self.source_location_id.complete_name))

#         # ── 2. Already-registered check (exclude current asset) ───────────────
#         exclude_id = asset.id if asset else 0
#         already = self.env['account.asset'].search([
#             ('lot_id',      '=', self.lot_id.id),
#             ('asset_state', 'not in', ['draft']),
#             ('id',          '!=', exclude_id),
#         ], limit=1)
#         if already:
#             raise UserError(_(
#                 'Serial number "%s" is already registered as asset %s.'
#             ) % (self.lot_id.name, already.code))

#         # ── 3. Row-level lock ─────────────────────────────────────────────────
#         self.env.cr.execute(
#             'SELECT id FROM stock_lot WHERE id = %s FOR UPDATE NOWAIT',
#             (self.lot_id.id,)
#         )

#         # ── 4. Resolve asset location ─────────────────────────────────────────
#         asset_location = (
#             self.env.company.asset_location_id
#             or self.env.ref(
#                 'asset_management_bdcalling.asset_stock_location',
#                 raise_if_not_found=False,
#             )
#         )
#         if not asset_location:
#             raise UserError(_(
#                 'No default Asset Location configured. '
#                 'Go to Asset Management → Configuration → Settings.'
#             ))

#         # ── 5. Validate category accounting config ────────────────────────────
#         cat = self.category_id
#         missing = [
#             label for field_name, label in [
#                 ('account_asset_id',               'Asset Account'),
#                 ('account_depreciation_id',        'Accumulated Depreciation Account'),
#                 ('account_depreciation_expense_id','Depreciation Expense Account'),
#                 ('journal_id',                     'Asset Journal'),
#                 ('method',                         'Depreciation Method'),
#                 ('method_number',                  'Number of Depreciation Entries'),
#             ]
#             if not getattr(cat, field_name, False)
#         ]
#         if missing:
#             raise UserError(_(
#                 'Asset category "%s" is missing required accounting configuration:\n\n'
#                 '  • %s\n\n'
#                 'Go to Accounting → Configuration → Asset Models to complete the setup.'
#             ) % (cat.name, '\n  • '.join(missing)))

#         # ── 6. Stock move: source_location → asset_location ───────────────────
#         self._create_registration_move(asset_location)

#         # ── 7. Write all fields onto the AMS asset record ─────────────────────
#         non_dep_pct = getattr(cat, 'prorata_value', 0.0) or 0.0

#         ams_vals = {
#             # Native accounting fields (required before validate())
#             'model_id':                         cat.id,
#             'original_value':                   self.purchase_price,
#             'salvage_value':                     self.purchase_price * (non_dep_pct / 100.0),
#             'acquisition_date':                  self.purchase_date or fields.Date.today(),
#             'account_asset_id':                  cat.account_asset_id.id,
#             'account_depreciation_id':           cat.account_depreciation_id.id,
#             'account_depreciation_expense_id':   cat.account_depreciation_expense_id.id,
#             'journal_id':                        cat.journal_id.id,
#             'method':                            cat.method,
#             'method_number':                     cat.method_number,
#             'method_period':                     cat.method_period,
#             'prorata_computation_type':          cat.prorata_computation_type,
#             # AMS-specific fields
#             'purchase_price':                    self.purchase_price,
#             'purchase_date':                     self.purchase_date,
#             'registration_date':                 fields.Date.today(),
#             'location_id':                       asset_location.id,
#         }
#         if self.notes:
#             ams_vals['notes'] = self.notes

#         if asset:
#             asset.write(ams_vals)
#         else:
#             ams_vals.update({
#                 'product_id': self.product_id.id,
#                 'lot_id':     self.lot_id.id,
#                 'company_id': self.company_id.id,
#             })
#             asset = self.env['account.asset'].create(ams_vals)

#         # ── 8. validate() — generates native depreciation board ───────────────
#         # Sets native state = 'open' and creates all account.move depreciation
#         # entries. The "Depreciation Board" tab in Odoo 19 appears automatically.
#         try:
#             asset.validate()
#         except UserError:
#             raise
#         except Exception as exc:
#             _logger.error(
#                 'AMS: validate() failed for asset %s: %s', asset.code, exc
#             )
#             raise UserError(_(
#                 'Failed to generate the depreciation schedule for "%s".\n\n'
#                 'Error: %s\n\n'
#                 'Verify the accounting configuration in category "%s".'
#             ) % (asset.name, exc, cat.name))

#         # ── 9. Set AMS lifecycle state = 'available' ──────────────────────────
#         asset.write({'asset_state': 'available'})

#         # ── 10. Log history ───────────────────────────────────────────────────
#         metadata = {
#             'source_location': self.source_location_id.complete_name,
#         }
#         if self.purchase_order_id:
#             metadata['purchase_order'] = self.purchase_order_id.name
#         asset._log_history(
#             event_type='register',
#             old_state='draft',
#             new_state='available',
#             description=_('Asset registered by %s') % self.env.user.name,
#             metadata=metadata,
#         )

#         return {
#             'type':      'ir.actions.act_window',
#             'name':      _('Asset'),
#             'res_model': 'account.asset',
#             'res_id':    asset.id,
#             'view_mode': 'form',
#             'target':    'current',
#         }

#     # =========================================================================
#     # STOCK MOVE HELPER
#     # =========================================================================

#     def _create_registration_move(self, asset_location):
#         """
#         stock.move: source_location_id → asset_location (qty=1, serial tracked).
#         Validates immediately so on-hand inventory is decremented.
#         """
#         move = self.env['stock.move'].create({
#             'name':             _('Asset Registration: %s') % self.lot_id.name,
#             'product_id':       self.product_id.id,
#             'product_uom':      self.product_id.uom_id.id,
#             'product_uom_qty':  1.0,
#             'location_id':      self.source_location_id.id,
#             'location_dest_id': asset_location.id,
#             'origin':           _('Asset Registration'),
#             'state':            'draft',
#             'company_id':       self.company_id.id,
#         })
#         self.env['stock.move.line'].create({
#             'move_id':          move.id,
#             'product_id':       self.product_id.id,
#             'lot_id':           self.lot_id.id,
#             'quantity':         1.0,
#             'location_id':      self.source_location_id.id,
#             'location_dest_id': asset_location.id,
#             'company_id':       self.company_id.id,
#         })
#         move._action_confirm()
#         move._action_assign()
#         move.move_line_ids.quantity = 1.0
#         move._action_done()
#         return move

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AssetRegisterWizard(models.TransientModel):
    _name = 'asset.register.wizard'
    _description = 'Asset Registration Wizard'

    # Pre-filled via context (default_asset_id) when opened from asset form.
    asset_id = fields.Many2one(
        'account.asset',
        string='Asset Record',
        readonly=True,
    )

    # ── Serial / Product ──────────────────────────────────────────────────────
    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number',
        required=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        compute='_compute_from_lot',
        store=True,
        readonly=False,
    )

    # ── Auto-filled from Purchase Order via lot ───────────────────────────────
    purchase_price = fields.Monetary(
        string='Purchase Price',
        currency_field='currency_id',
        required=True,
        help='Auto-filled from the Purchase Order line that received this serial.',
    )
    purchase_date = fields.Date(
        string='Purchase Date',
        help='Auto-filled from the Purchase Order confirmation date.',
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Source Purchase Order',
        readonly=True,
    )
    purchase_order_line_id = fields.Many2one(
        'purchase.order.line',
        string='Purchase Order Line',
        readonly=True,
    )

    # ── Category ──────────────────────────────────────────────────────────────
    # category_domain_ids feeds the domain on category_id so that ALL asset
    # model records visible to this user (across allowed companies) are shown.
    # We load them with sudo() to avoid the native multi-company rule blocking
    # category records that belong to a company the user can switch to.
    category_domain_ids = fields.Many2many(
        'account.asset',
        compute='_compute_category_domain_ids',
        string='Category Domain',
    )
    category_id = fields.Many2one(
        'account.asset',
        string='Asset Category',
        required=True,
        domain="[('id', 'in', category_domain_ids)]",
    )

    # ── Location & misc ───────────────────────────────────────────────────────
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        required=True,
        domain="[('usage', 'in', ['internal', 'transit'])]",
        default=lambda self: self.env.ref(
            'stock.stock_location_stock', raise_if_not_found=False
        ),
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    # Lots already locked by a registered (non-draft) AMS asset.
    registered_lot_ids = fields.Many2many(
        'stock.lot',
        compute='_compute_registered_lot_ids',
        string='Already Registered Serials',
    )

    # =========================================================================
    # COMPUTE
    # =========================================================================

    @api.depends_context('uid')
    def _compute_registered_lot_ids(self):
        """Lots locked by any non-draft AMS asset — excluded from lot domain."""
        locked = self.env['account.asset'].sudo().search([
            ('lot_id',      '!=', False),
            ('asset_state', 'not in', ['draft']),
        ]).mapped('lot_id')
        for rec in self:
            rec.registered_lot_ids = locked

    @api.depends_context('uid', 'allowed_company_ids')
    def _compute_category_domain_ids(self):
        """
        Load ALL account.asset model records (state='model') with sudo() so
        the native multi-company record rule on account.asset does not block
        categories that belong to other companies.

        We still filter by the companies the user is allowed to switch to
        (env.user.company_ids) plus global categories (company_id=False).
        """
        allowed_company_ids = self.env.user.company_ids.ids
        categories = self.env['account.asset'].sudo().search([
            ('state', '=', 'model'),
            '|',
            ('company_id', '=', False),
            ('company_id', 'in', allowed_company_ids),
        ])
        for rec in self:
            rec.category_domain_ids = categories

    @api.depends('lot_id')
    def _compute_from_lot(self):
        """
        When a serial/lot is selected, auto-fill:
          - product_id           from lot.product_id
          - purchase_price       from the PO line unit price (currency-converted)
          - purchase_date        from PO confirmation/order date
          - purchase_order_id    for display/traceability
          - purchase_order_line_id

        Lookup path (Odoo 19):
          stock.lot
            → stock.move.line  (lot_id, state='done')
              → stock.move     (move_id.purchase_line_id != False)
                → purchase.order.line  (price_unit, order_id)
                  → purchase.order     (date_approve, currency_id)

        All reads use sudo() to cross company boundaries safely — the PO and
        stock moves may belong to a different company than the wizard's context.
        """
        for rec in self:
            if not rec.lot_id:
                rec.product_id             = False
                rec.purchase_price         = 0.0
                rec.purchase_date          = False
                rec.purchase_order_id      = False
                rec.purchase_order_line_id = False
                continue

            # Product is always taken from the lot itself
            rec.product_id = rec.lot_id.product_id

            # ── Find the most recent done receipt move line for this lot ──────
            # sudo() is required: the move line / PO may belong to a different
            # company than the user's current active company.
            move_line = self.env['stock.move.line'].sudo().search([
                ('lot_id',                   '=', rec.lot_id.id),
                ('state',                    '=', 'done'),
                ('move_id.purchase_line_id', '!=', False),
            ], order='date desc', limit=1)

            if not move_line:
                # No PO receipt found — leave for manual entry
                rec.purchase_price         = 0.0
                rec.purchase_date          = False
                rec.purchase_order_id      = False
                rec.purchase_order_line_id = False
                continue

            po_line = move_line.move_id.purchase_line_id
            po      = po_line.order_id

            # ── Currency conversion (PO currency → company currency) ──────────
            price_unit = po_line.price_unit
            company_currency = rec.currency_id or self.env.company.currency_id
            if po.currency_id and po.currency_id != company_currency:
                price_unit = po.currency_id._convert(
                    price_unit,
                    company_currency,
                    rec.company_id or self.env.company,
                    po.date_approve or fields.Date.today(),
                )

            rec.purchase_price         = price_unit
            rec.purchase_date          = po.date_approve or po.date_order
            rec.purchase_order_id      = po
            rec.purchase_order_line_id = po_line

    # =========================================================================
    # ACTION
    # =========================================================================

    def action_register(self):
        self.ensure_one()

        # ── 0. Resolve which AMS asset we are registering ─────────────────────
        asset = self.asset_id
        if not asset:
            asset = self.env['account.asset'].sudo().search([
                ('lot_id',      '=', self.lot_id.id),
                ('asset_state', '=', 'draft'),
            ], limit=1)

        # ── 1. Inventory check ────────────────────────────────────────────────
        quant = self.env['stock.quant'].sudo().search([
            ('lot_id',      '=', self.lot_id.id),
            ('location_id', '=', self.source_location_id.id),
        ], limit=1)
        if not quant or quant.quantity < 1:
            raise UserError(_(
                'Serial number "%s" is not available (qty < 1) in location "%s".'
            ) % (self.lot_id.name, self.source_location_id.complete_name))

        # ── 2. Already-registered check ───────────────────────────────────────
        exclude_id = asset.id if asset else 0
        already = self.env['account.asset'].sudo().search([
            ('lot_id',      '=', self.lot_id.id),
            ('asset_state', 'not in', ['draft']),
            ('id',          '!=', exclude_id),
        ], limit=1)
        if already:
            raise UserError(_(
                'Serial number "%s" is already registered as asset %s.'
            ) % (self.lot_id.name, already.code))

        # ── 3. Row-level lock ─────────────────────────────────────────────────
        self.env.cr.execute(
            'SELECT id FROM stock_lot WHERE id = %s FOR UPDATE NOWAIT',
            (self.lot_id.id,)
        )

        # ── 4. Resolve asset location ─────────────────────────────────────────
        asset_location = (
            self.env.company.asset_location_id
            or self.env.ref(
                'asset_management_bdcalling.asset_stock_location',
                raise_if_not_found=False,
            )
        )
        if not asset_location:
            raise UserError(_(
                'No default Asset Location configured. '
                'Go to Asset Management → Configuration → Settings.'
            ))

        # ── 5. Validate category accounting config ────────────────────────────
        # Use sudo() to read category fields — the category may belong to a
        # different company and the native rule would block the read otherwise.
        cat = self.category_id.sudo()

        missing = [
            label for field_name, label in [
                ('account_asset_id',               'Asset Account'),
                ('account_depreciation_id',        'Accumulated Depreciation Account'),
                ('account_depreciation_expense_id','Depreciation Expense Account'),
                ('journal_id',                     'Asset Journal'),
                ('method',                         'Depreciation Method'),
                ('method_number',                  'Number of Depreciation Entries'),
            ]
            if not getattr(cat, field_name, False)
        ]
        if missing:
            raise UserError(_(
                'Asset category "%s" is missing required accounting configuration:\n\n'
                '  • %s\n\n'
                'Go to Accounting → Configuration → Asset Models to complete the setup.'
            ) % (cat.name, '\n  • '.join(missing)))

        # ── 6. Stock move: source_location → asset_location ───────────────────
        self._create_registration_move(asset_location)

        # ── 7. Write all fields onto the AMS asset record ─────────────────────
        non_dep_pct = getattr(cat, 'prorata_value', 0.0) or 0.0

        ams_vals = {
            # Native accounting fields (required before validate())
            'model_id':                         cat.id,
            'original_value':                   self.purchase_price,
            'salvage_value':                     self.purchase_price * (non_dep_pct / 100.0),
            'acquisition_date':                  self.purchase_date or fields.Date.today(),
            'account_asset_id':                  cat.account_asset_id.id,
            'account_depreciation_id':           cat.account_depreciation_id.id,
            'account_depreciation_expense_id':   cat.account_depreciation_expense_id.id,
            'journal_id':                        cat.journal_id.id,
            'method':                            cat.method,
            'method_number':                     cat.method_number,
            'method_period':                     cat.method_period,
            'prorata_computation_type':          cat.prorata_computation_type,
            # AMS fields
            'purchase_price':                    self.purchase_price,
            'purchase_date':                     self.purchase_date,
            'registration_date':                 fields.Date.today(),
            'location_id':                       asset_location.id,
        }
        if self.notes:
            ams_vals['notes'] = self.notes

        if asset:
            asset.sudo().write(ams_vals)
        else:
            ams_vals.update({
                'product_id': self.product_id.id,
                'lot_id':     self.lot_id.id,
                'company_id': self.company_id.id,
            })
            asset = self.env['account.asset'].sudo().create(ams_vals)

        # ── 8. validate() — generates native depreciation board ───────────────
        # validate() sets native state='open' and creates all account.move
        # depreciation entries. The "Depreciation Board" tab appears in the form.
        try:
            asset.sudo().validate()
        except UserError:
            raise
        except Exception as exc:
            _logger.error(
                'AMS: validate() failed for asset %s: %s', asset.code, exc
            )
            raise UserError(_(
                'Failed to generate the depreciation schedule for "%s".\n\n'
                'Error: %s\n\n'
                'Verify the accounting configuration in category "%s".'
            ) % (asset.name, exc, cat.name))

        # ── 9. Set AMS lifecycle state = 'available' ──────────────────────────
        asset.sudo().write({'asset_state': 'available'})

        # ── 10. Log history ───────────────────────────────────────────────────
        metadata = {'source_location': self.source_location_id.complete_name}
        if self.purchase_order_id:
            metadata['purchase_order'] = self.purchase_order_id.name
        asset._log_history(
            event_type='register',
            old_state='draft',
            new_state='available',
            description=_('Asset registered by %s') % self.env.user.name,
            metadata=metadata,
        )

        return {
            'type':      'ir.actions.act_window',
            'name':      _('Asset'),
            'res_model': 'account.asset',
            'res_id':    asset.id,
            'view_mode': 'form',
            'target':    'current',
        }

    # =========================================================================
    # STOCK MOVE HELPER
    # =========================================================================

    def _create_registration_move(self, asset_location):
        """
        stock.move: source_location → asset_location (qty=1, serial tracked).
        Completes immediately — decrements on-hand inventory.
        """
        move = self.env['stock.move'].create({
            'name':             _('Asset Registration: %s') % self.lot_id.name,
            'product_id':       self.product_id.id,
            'product_uom':      self.product_id.uom_id.id,
            'product_uom_qty':  1.0,
            'location_id':      self.source_location_id.id,
            'location_dest_id': asset_location.id,
            'origin':           _('Asset Registration'),
            'state':            'draft',
            'company_id':       self.company_id.id,
        })
        self.env['stock.move.line'].create({
            'move_id':          move.id,
            'product_id':       self.product_id.id,
            'lot_id':           self.lot_id.id,
            'quantity':         1.0,
            'location_id':      self.source_location_id.id,
            'location_dest_id': asset_location.id,
            'company_id':       self.company_id.id,
        })
        move._action_confirm()
        move._action_assign()
        move.move_line_ids.quantity = 1.0
        move._action_done()
        return move