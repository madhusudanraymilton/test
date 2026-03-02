# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo import fields
from .common import AssetTestCommon


@tagged('post_install', '-at_install', 'asset_assign')
class TestAssetAssign(AssetTestCommon):

    def test_assign_available_asset(self):
        """AM-06: Assign an available asset to an employee."""
        asset = self._register_asset(serial='SN-ASGN-001')
        self.assertEqual(asset.state, 'available')

        wizard = self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
            'condition_on_assign': 'good',
        })
        wizard.action_assign()

        self.assertEqual(asset.state, 'assigned')
        self.assertEqual(asset.current_employee_id, self.employee)

        # Check assignment record
        assignment = self.env['asset.assignment'].search([
            ('asset_id', '=', asset.id),
            ('is_active', '=', True),
        ], limit=1)
        self.assertTrue(assignment)
        self.assertEqual(assignment.employee_id, self.employee)
        self.assertFalse(assignment.return_date)

    def test_assign_non_available_raises(self):
        """AM-06: Assigning a non-available (draft) asset raises UserError."""
        lot = self._create_lot('SN-ASGN-NON-001')
        asset = self.env['asset.asset'].create({
            'product_id': self.product.id,
            'lot_id': lot.id,
            'category_id': self.category.id,
            'purchase_price': 1000.0,
            'state': 'draft',
        })
        wizard = self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
        })
        with self.assertRaises(UserError):
            wizard.action_assign()

    def test_double_assign_raises(self):
        """AM-06: Assigning an already-assigned asset raises UserError."""
        asset = self._register_asset(serial='SN-DBL-ASGN-001')

        wizard1 = self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
        })
        wizard1.action_assign()
        self.assertEqual(asset.state, 'assigned')

        wizard2 = self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
        })
        with self.assertRaises(UserError):
            wizard2.action_assign()

    def test_return_asset_updates_state(self):
        """AM-07: Returning an asset sets state back to available."""
        asset = self._register_asset(serial='SN-RET-001')

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
        self.assertFalse(asset.current_employee_id)

        # Check assignment is closed
        assignment = self.env['asset.assignment'].search([
            ('asset_id', '=', asset.id),
        ], limit=1)
        self.assertFalse(assignment.is_active)
        self.assertEqual(assignment.return_date, fields.Date.today())

    def test_return_damaged_creates_activity(self):
        """AM-07: Returning damaged asset creates a mail.activity."""
        asset = self._register_asset(serial='SN-DMG-001')

        self.env['asset.assign.wizard'].create({
            'asset_id': asset.id,
            'employee_id': self.employee.id,
            'assign_date': fields.Date.today(),
        }).action_assign()

        activity_count_before = self.env['mail.activity'].search_count([
            ('res_model', '=', 'asset.asset'),
            ('res_id', '=', asset.id),
        ])

        self.env['asset.return.wizard'].create({
            'asset_id': asset.id,
            'return_date': fields.Date.today(),
            'condition_on_return': 'damaged',
        }).action_return()

        activity_count_after = self.env['mail.activity'].search_count([
            ('res_model', '=', 'asset.asset'),
            ('res_id', '=', asset.id),
        ])
        self.assertGreater(activity_count_after, activity_count_before)

    def test_return_not_assigned_raises(self):
        """AM-07: Returning an available asset raises UserError."""
        asset = self._register_asset(serial='SN-RET-NA-001')
        self.assertEqual(asset.state, 'available')

        with self.assertRaises(UserError):
            self.env['asset.return.wizard'].create({
                'asset_id': asset.id,
                'return_date': fields.Date.today(),
                'condition_on_return': 'good',
            }).action_return()
