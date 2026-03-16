# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AssetRegisterWizard(models.TransientModel):
    _name = 'asset.register.wizard'
    _description = 'Asset Registration Wizard'

    lot_id = fields.Many2one(
        'stock.lot',
        string='Serial Number',
        required=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        compute='_compute_product_id',
        store=True,
        readonly=False,
    )
    category_id = fields.Many2one(
        'account.asset',
        string='Asset Category',
        required=True,
        domain="[('state', '=', 'model'), ('company_id', 'in', [company_id, False])]",
    )
    purchase_price = fields.Monetary(
        string='Purchase Price',
        currency_field='currency_id',
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    purchase_date = fields.Date(
        string='Purchase Date',
        default=fields.Date.today,
    )
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        required=True,
        domain="[('usage', 'in', ['internal', 'transit'])]",
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    registered_lot_ids = fields.Many2many(
        'stock.lot',
        compute='_compute_registered_lot_ids',
        string='Already Registered Serials',
        help='Lots locked by non-draft assets — excluded from the selection domain.',
    )

    @api.depends_context('uid')
    def _compute_registered_lot_ids(self):
        locked = self.env['account.asset'].search([
            ('lot_id', '!=', False),
            ('state', '!=', 'draft'),
        ]).mapped('lot_id')
        for rec in self:
            rec.registered_lot_ids = locked

    @api.depends('lot_id')
    def _compute_product_id(self):
        for rec in self:
            rec.product_id = rec.lot_id.product_id if rec.lot_id else False

    def action_register(self):
        self.ensure_one()

        # ── 1. Validate inventory availability ───────────────────────────────
        quant = self.env['stock.quant'].search([
            ('lot_id', '=', self.lot_id.id),
            ('location_id', '=', self.source_location_id.id),
        ], limit=1)

        if not quant or quant.quantity < 1:
            raise UserError(_(
                'Serial number "%s" is not available (qty < 1) in location "%s".'
            ) % (self.lot_id.name, self.source_location_id.complete_name))

        # ── 2. Check not already registered ──────────────────────────────────
        active_asset = self.env['account.asset'].search([
            ('lot_id', '=', self.lot_id.id),
            ('state', '!=', 'draft'),
        ], limit=1)
        if active_asset:
            raise UserError(_(
                'Serial number "%s" is already registered as asset %s.'
            ) % (self.lot_id.name, active_asset.code))

        # ── 3. Lock lot row to prevent concurrent registration ────────────────
        self.env.cr.execute(
            'SELECT id FROM stock_lot WHERE id = %s FOR UPDATE NOWAIT',
            (self.lot_id.id,)
        )

        # ── 4. Determine asset location ───────────────────────────────────────
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
                'Please set it in Configuration > Settings.'
            ))

        # ── 5. Create and validate stock move ─────────────────────────────────
        move = self._create_registration_move(asset_location)

        # ── 6. Create asset record ────────────────────────────────────────────
        existing_draft = self.env['account.asset'].search([
            ('lot_id', '=', self.lot_id.id),
            ('state', '=', 'draft'),
        ], limit=1)

        if existing_draft:
            existing_draft.write({
                'category_id': self.category_id.id,
                'purchase_price': self.purchase_price,
                'currency_id': self.currency_id.id,
                'purchase_date': self.purchase_date,
                'registration_date': fields.Date.today(),
                'state': 'available',
                'location_id': asset_location.id,
                'notes': self.notes or existing_draft.notes,
            })
            asset = existing_draft
        else:
            asset = self.env['account.asset'].create({
                'product_id': self.product_id.id,
                'lot_id': self.lot_id.id,
                'category_id': self.category_id.id,
                'purchase_price': self.purchase_price,
                'currency_id': self.currency_id.id,
                'purchase_date': self.purchase_date,
                'registration_date': fields.Date.today(),
                'state': 'available',
                'location_id': asset_location.id,
                'company_id': self.company_id.id,
                'notes': self.notes,
            })
        # ── 7. Generate depreciation board ────────────────────────────────────
        # asset._generate_depreciation_board()
        # cat = self.category_id  # account.asset with state='model'
        # non_dep_pct = getattr(cat, 'prorata_value', 0.0)

        # odoo_asset = self.env['account.asset'].create({
        #     'name':                              asset.name,
        #     'model_id':                          cat.id,
        #     'original_value':                    self.purchase_price,
        #     'salvage_value':                     self.purchase_price * (non_dep_pct / 100.0),
        #     'acquisition_date':                  self.purchase_date or fields.Date.today(),
        #     'account_asset_id':                  cat.account_asset_id.id,
        #     'account_depreciation_id':           cat.account_depreciation_id.id,
        #     'account_depreciation_expense_id':   cat.account_depreciation_expense_id.id,
        #     'journal_id':                        cat.journal_id.id,
        #     'method':                            cat.method,           # 'linear'/'degressive'
        #     'method_number':                     cat.method_number,    # total entries
        #     'method_period':                     cat.method_period,    # '1'=monthly,'12'=yearly
        #     'prorata_computation_type':          cat.prorata_computation_type,
        #     'company_id':                        self.company_id.id,
        # })
        # odoo_asset.validate()          # draft → open, generates depreciation board
        # asset.write({'odoo_asset_id': odoo_asset.id})

         # ── 7. Create & validate native accounting asset ──────────────────────
        cat = self.category_id

        # Guard: surface missing config immediately instead of silent failure
        missing = []
        if not cat.account_asset_id:
            missing.append('Asset Account (account_asset_id)')
        if not cat.account_depreciation_id:
            missing.append('Accumulated Depreciation Account')
        if not cat.account_depreciation_expense_id:
            missing.append('Depreciation Expense Account')
        if not cat.journal_id:
            missing.append('Asset Journal')
        if not cat.method:
            missing.append('Depreciation Method')
        if not cat.method_number:
            missing.append('Number of Depreciation Entries')
        if missing:
            raise UserError(_(
                'Asset category "%s" is missing required accounting configuration:\n\n'
                '  • %s\n\n'
                'Go to Accounting → Configuration → Asset Models and complete the setup.'
            ) % (cat.name, '\n  • '.join(missing)))

        non_dep_pct = getattr(cat, 'prorata_value', 0.0) or 0.0

        try:
            odoo_asset = self.env['account.asset'].create({
                'name':                             asset.name,
                'model_id':                         cat.id,
                'original_value':                   self.purchase_price,
                'salvage_value':                    self.purchase_price * (non_dep_pct / 100.0),
                'acquisition_date':                 self.purchase_date or fields.Date.today(),
                'account_asset_id':                 cat.account_asset_id.id,
                'account_depreciation_id':          cat.account_depreciation_id.id,
                'account_depreciation_expense_id':  cat.account_depreciation_expense_id.id,
                'journal_id':                       cat.journal_id.id,
                'method':                           cat.method,
                'method_number':                    cat.method_number,
                'method_period':                    cat.method_period,
                'prorata_computation_type':         cat.prorata_computation_type,
                'company_id':                       self.company_id.id,
            })
            odoo_asset.validate()
            asset.write({'odoo_asset_id': odoo_asset.id})
            _logger.info(
                'AMS: Native accounting asset %s created for asset %s',
                odoo_asset.id, asset.code,
            )
        except UserError:
            raise  # re-raise clean UserErrors as-is
        except Exception as exc:
            _logger.error(
                'AMS: Failed to create native accounting asset for %s: %s',
                asset.code, exc,
            )
            raise UserError(_(
                'Failed to generate depreciation schedule for "%s".\n\n'
                'Error: %s\n\n'
                'Verify that category "%s" has complete accounting setup in '
                'Accounting → Configuration → Asset Models.'
            ) % (asset.name, str(exc), cat.name))

        # ── 8. Log history ────────────────────────────────────────────────────
        asset._log_history(
            event_type='register',
            old_state='draft',
            new_state='available',
            description=_('Asset registered by %s') % self.env.user.name,
            metadata={'source_location': self.source_location_id.complete_name},
        )

        # ── 9. Return action to open the new asset ────────────────────────────
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset'),
            'res_model': 'account.asset',
            'res_id': asset.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_registration_move(self, asset_location):
        """Create and validate a stock move: source → asset_location."""
        move = self.env['stock.move'].create({
            'name': _('Asset Registration: %s') % self.lot_id.name,
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_id.id,
            'product_uom_qty': 1.0,
            'location_id': self.source_location_id.id,
            'location_dest_id': asset_location.id,
            'origin': _('Asset Registration'),
            'state': 'draft',
            'company_id': self.company_id.id,
        })
        self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': self.product_id.id,
            'lot_id': self.lot_id.id,
            'quantity': 1.0,
            'location_id': self.source_location_id.id,
            'location_dest_id': asset_location.id,
            'company_id': self.company_id.id,
        })
        move._action_confirm()
        move._action_assign()
        move.move_line_ids.quantity = 1.0
        move._action_done() 
        return move
