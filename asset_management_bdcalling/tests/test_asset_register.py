# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo import fields
from .common import AssetTestCommon


@tagged('post_install', '-at_install', 'asset_register')
class TestAssetRegister(AssetTestCommon):

    def test_register_asset_decreases_inventory(self):
        lot = self._create_lot('SN-REG-INV-001')
        self._add_to_inventory(lot, qty=1.0)
        initial_qty = self._get_inventory_qty(lot)
        self.assertEqual(initial_qty, 1.0)
        asset = self._register_asset(lot=lot)
        post_qty = self._get_inventory_qty(lot)
        self.assertEqual(post_qty, 0.0)
        self.assertEqual(asset.state, 'available')
        self.assertTrue(asset.code.startswith('AST/'))

    def test_register_creates_depreciation_schedule(self):
        asset = self._register_asset(serial='SN-REG-DEP-001', purchase_price=36000.0)
        self.assertEqual(len(asset.depreciation_line_ids), self.category.duration_months)
        self.assertTrue(all(not l.move_posted_check for l in asset.depreciation_line_ids))
        first_line = asset.depreciation_line_ids.sorted('sequence')[0]
        expected = round(36000.0 / 36, 2)
        self.assertAlmostEqual(first_line.amount, expected, delta=0.02)

    def test_register_sets_registration_date(self):
        asset = self._register_asset(serial='SN-REG-DATE-001')
        self.assertEqual(asset.registration_date, fields.Date.today())

    def test_register_duplicate_serial_raises(self):
        lot = self._create_lot('SN-DUP-001')
        self._add_to_inventory(lot, qty=1.0)
        self._register_asset(lot=lot)
        self._add_to_inventory(lot, qty=1.0)
        wizard2 = self.env['asset.register.wizard'].create({
            'lot_id': lot.id,
            'category_id': self.category.id,
            'purchase_price': 1000.0,
            'source_location_id': self.stock_location.id,
        })
        with self.assertRaises(UserError):
            wizard2.action_register()

    def test_register_insufficient_inventory_raises(self):
        lot = self._create_lot('SN-NO-INV-001')
        wizard = self.env['asset.register.wizard'].create({
            'lot_id': lot.id,
            'category_id': self.category.id,
            'purchase_price': 5000.0,
            'source_location_id': self.stock_location.id,
        })
        with self.assertRaises(UserError):
            wizard.action_register()

    def test_unregister_restores_inventory(self):
        asset = self._register_asset(serial='SN-UNREG-001')
        lot = asset.lot_id
        pre_unreg_qty = self._get_inventory_qty(lot)
        self.assertEqual(pre_unreg_qty, 0.0)
        wizard = self.env['asset.unregister.wizard'].create({
            'asset_id': asset.id,
            'reason': 'Test unregistration',
            'destination_location_id': self.stock_location.id,
        })
        wizard.action_unregister()
        self.assertEqual(asset.state, 'draft')
        post_qty = self._get_inventory_qty(lot)
        self.assertEqual(post_qty, 1.0)
        self.assertEqual(len(asset.depreciation_line_ids), 0)

    def test_unregister_while_assigned_raises(self):
        asset = self._register_asset(serial='SN-UNREG-ASGN-001')
        self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
        }).action_assign()
        self.assertEqual(asset.state, 'assigned')
        wizard = self.env['asset.unregister.wizard'].create({
            'asset_id': asset.id,
            'reason': 'Should fail',
            'destination_location_id': self.stock_location.id,
        })
        with self.assertRaises(UserError):
            wizard.action_unregister()
