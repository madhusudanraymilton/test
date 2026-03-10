# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo import fields
from .common import AssetTestCommon


@tagged('post_install', '-at_install', 'asset_lifecycle')
class TestAssetLifecycle(AssetTestCommon):

    def test_full_lifecycle_draft_to_disposed(self):
        asset = self._register_asset(serial='SN-LC-001')
        self.assertEqual(asset.state, 'available')
        self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
        }).action_assign()
        self.assertEqual(asset.state, 'assigned')
        self.env['asset.return.wizard'].create({
            'asset_id': asset.id,
            'return_date': fields.Date.today(),
            'condition_on_return': 'good',
        }).action_return()
        self.assertEqual(asset.state, 'available')
        asset.action_dispose()
        self.assertEqual(asset.state, 'disposed')
        event_types = asset.history_ids.sorted('event_date').mapped('event_type')
        self.assertIn('register', event_types)
        self.assertIn('assign', event_types)
        self.assertIn('return', event_types)
        self.assertIn('dispose', event_types)

    def test_state_machine_invalid_transitions(self):
        lot = self._create_lot('SN-INVALID-001')
        asset = self.env['asset.asset'].create({
            'product_id': self.product.id,
            'lot_id': lot.id,
            'category_id': self.category.id,
            'purchase_price': 1000.0,
            'state': 'draft',
        })
        with self.assertRaises(UserError):
            self.env['asset.assign.wizard'].create({
                'asset_id': asset.id,
                'employee_id': self.employee.id,
                'assign_date': fields.Date.today(),
            }).action_assign()
        with self.assertRaises(UserError):
            self.env['asset.return.wizard'].create({
                'asset_id': asset.id,
                'return_date': fields.Date.today(),
                'condition_on_return': 'good',
            }).action_return()
        with self.assertRaises(UserError):
            asset.action_scrap()
        with self.assertRaises(UserError):
            asset.action_dispose()

    def test_history_immutability_write_raises(self):
        asset = self._register_asset(serial='SN-HIST-W-001')
        history = asset.history_ids[0]
        with self.assertRaises(UserError):
            history.write({'description': 'Tampered'})

    def test_history_immutability_unlink_raises(self):
        asset = self._register_asset(serial='SN-HIST-D-001')
        history = asset.history_ids[0]
        with self.assertRaises(UserError):
            history.unlink()

    def test_history_record_count(self):
        asset = self._register_asset(serial='SN-HIST-COUNT-001')
        self.assertEqual(len(asset.history_ids), 1)
        self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
        }).action_assign()
        self.assertEqual(len(asset.history_ids), 2)
        self.env['asset.return.wizard'].create({
            'asset_id': asset.id,
            'return_date': fields.Date.today(),
            'condition_on_return': 'fair',
        }).action_return()
        self.assertEqual(len(asset.history_ids), 3)

    def test_multi_company_isolation(self):
        company_b = self.env['res.company'].create({'name': 'Test Company B'})
        lot = self._create_lot('SN-MC-001')
        self._add_to_inventory(lot)
        asset = self._register_asset(lot=lot)
        self.assertEqual(asset.company_id, self.env.company)
        assets_from_b = self.env['asset.asset'].with_company(company_b).search([
            ('id', '=', asset.id),
        ])
        self.assertFalse(assets_from_b)

    def test_asset_code_uniqueness(self):
        asset1 = self._register_asset(serial='SN-CODE-001')
        asset2 = self._register_asset(serial='SN-CODE-002')
        self.assertNotEqual(asset1.code, asset2.code)
        self.assertTrue(asset1.code.startswith('AST/'))
        self.assertTrue(asset2.code.startswith('AST/'))

    def test_scrap_assigned_asset(self):
        asset = self._register_asset(serial='SN-SCRAP-001')
        self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
        }).action_assign()
        self.assertEqual(asset.state, 'assigned')
        asset.action_scrap()
        self.assertEqual(asset.state, 'scrapped')
        self.assertFalse(asset.current_employee_id)
        self.assertIn('scrap', asset.history_ids.mapped('event_type'))
