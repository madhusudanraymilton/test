# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields


class AssetTestCommon(TransactionCase):
    """Base class with shared helpers for all AMS test suites."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Accounts ──────────────────────────────────────────────────────────
        cls.account_asset = cls.env['account.account'].create({
            'name': 'Test Asset Account',
            'code': 'TST100',
            'account_type': 'asset_fixed',
            'company_id': cls.env.company.id,
        })
        cls.account_depreciation = cls.env['account.account'].create({
            'name': 'Test Accumulated Depreciation',
            'code': 'TST101',
            'account_type': 'asset_fixed',
            'company_id': cls.env.company.id,
        })
        cls.account_expense = cls.env['account.account'].create({
            'name': 'Test Depreciation Expense',
            'code': 'TST500',
            'account_type': 'expense',
            'company_id': cls.env.company.id,
        })

        # ── Journal ───────────────────────────────────────────────────────────
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Asset Journal',
            'code': 'TAST',
            'type': 'general',
            'company_id': cls.env.company.id,
        })

        # ── Asset Category (custom asset.category) ────────────────────────────
        cls.category = cls.env['asset.category'].create({
            'name': 'Test Laptops',
            'depreciation_method': 'straight_line',
            'duration_months': 36,
            'computation_method': 'monthly',
            'non_depreciable_pct': 0.0,
            'account_asset_id': cls.account_asset.id,
            'account_depreciation_id': cls.account_depreciation.id,
            'account_expense_id': cls.account_expense.id,
            'journal_id': cls.journal.id,
            'company_id': cls.env.company.id,
        })

        # ── Product ───────────────────────────────────────────────────────────
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product = cls.env['product.product'].create({
            'name': 'Test Laptop',
            'type': 'product',
            'tracking': 'serial',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
        })

        # ── Stock Locations ───────────────────────────────────────────────────
        cls.stock_location = cls.env.ref('stock.stock_location_stock')

        # FIX: corrected module ref from 'custom_asset_management' → 'asset_management_bdcalling'
        cls.asset_location = cls.env.ref(
            'asset_management_bdcalling.asset_stock_location',
            raise_if_not_found=False,
        )
        if not cls.asset_location:
            cls.asset_location = cls.env['stock.location'].create({
                'name': 'Asset Location (Test)',
                'usage': 'inventory',
            })

        cls.env.company.asset_location_id = cls.asset_location

        # ── Employee ──────────────────────────────────────────────────────────
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': cls.env.company.id,
        })

    def _create_lot(self, name='SN-TEST-001'):
        return self.env['stock.lot'].create({
            'name': name,
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })

    def _add_to_inventory(self, lot, qty=1.0, location=None):
        location = location or self.stock_location
        quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'lot_id': lot.id,
            'location_id': location.id,
            'quantity': qty,
        })
        return quant

    def _get_inventory_qty(self, lot, location=None):
        location = location or self.stock_location
        quant = self.env['stock.quant'].search([
            ('lot_id', '=', lot.id),
            ('location_id', '=', location.id),
        ], limit=1)
        return quant.quantity if quant else 0.0

    def _register_asset(self, lot=None, serial='SN-REG-001', purchase_price=50000.0):
        """Create a lot, add to inventory, run register wizard, return asset."""
        if lot is None:
            lot = self._create_lot(serial)
            self._add_to_inventory(lot)
        wizard = self.env['asset.register.wizard'].create({
            'lot_id': lot.id,
            'category_id': self.category.id,
            'purchase_price': purchase_price,
            'source_location_id': self.stock_location.id,
        })
        result = wizard.action_register()
        asset = self.env['asset.asset'].browse(result['res_id'])
        return asset
