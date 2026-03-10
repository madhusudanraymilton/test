# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged
from odoo.tools import mute_logger
from .common import AssetTestCommon


@tagged('post_install', '-at_install', 'asset_category')
class TestAssetCategory(AssetTestCommon):

    def test_create_valid_category(self):
        cat = self.env['asset.category'].create({
            'name': 'Test Servers',
            'depreciation_method': 'straight_line',
            'duration_months': 60,
            'computation_method': 'monthly',
            'non_depreciable_pct': 10.0,
            'account_asset_id': self.account_asset.id,
            'account_depreciation_id': self.account_depreciation.id,
            'account_expense_id': self.account_expense.id,
            'journal_id': self.journal.id,
        })
        self.assertEqual(cat.name, 'Test Servers')
        self.assertEqual(cat.depreciation_method, 'straight_line')
        self.assertEqual(cat.duration_months, 60)
        self.assertTrue(cat.active)

    def test_duplicate_name_same_company_raises(self):
        self.env['asset.category'].create({
            'name': 'Duplicate Cat',
            'depreciation_method': 'straight_line',
            'duration_months': 12,
            'computation_method': 'monthly',
            'account_asset_id': self.account_asset.id,
            'account_depreciation_id': self.account_depreciation.id,
            'account_expense_id': self.account_expense.id,
            'journal_id': self.journal.id,
        })
        with self.assertRaises(Exception):
            with mute_logger('odoo.sql_db'):
                self.env['asset.category'].create({
                    'name': 'Duplicate Cat',
                    'depreciation_method': 'straight_line',
                    'duration_months': 12,
                    'computation_method': 'monthly',
                    'account_asset_id': self.account_asset.id,
                    'account_depreciation_id': self.account_depreciation.id,
                    'account_expense_id': self.account_expense.id,
                    'journal_id': self.journal.id,
                })

    def test_invalid_duration_raises(self):
        with self.assertRaises(ValidationError):
            self.env['asset.category'].create({
                'name': 'Bad Duration Cat',
                'depreciation_method': 'straight_line',
                'duration_months': 0,
                'computation_method': 'monthly',
                'account_asset_id': self.account_asset.id,
                'account_depreciation_id': self.account_depreciation.id,
                'account_expense_id': self.account_expense.id,
                'journal_id': self.journal.id,
            })

    def test_non_depreciable_pct_out_of_range_raises(self):
        with self.assertRaises(ValidationError):
            self.env['asset.category'].create({
                'name': 'Bad Pct Cat',
                'depreciation_method': 'straight_line',
                'duration_months': 12,
                'computation_method': 'monthly',
                'non_depreciable_pct': 150.0,
                'account_asset_id': self.account_asset.id,
                'account_depreciation_id': self.account_depreciation.id,
                'account_expense_id': self.account_expense.id,
                'journal_id': self.journal.id,
            })

    def test_cannot_delete_category_with_assets(self):
        asset = self._register_asset(serial='SN-CAT-DEL-001')
        self.assertEqual(asset.category_id, self.category)
        with self.assertRaises(UserError):
            self.category.unlink()

    def test_journal_type_not_general_raises(self):
        sale_journal = self.env['account.journal'].create({
            'name': 'Test Sale Journal',
            'code': 'TSALE',
            'type': 'sale',
            'company_id': self.env.company.id,
        })
        with self.assertRaises(ValidationError):
            self.env['asset.category'].create({
                'name': 'Bad Journal Cat',
                'depreciation_method': 'straight_line',
                'duration_months': 12,
                'computation_method': 'monthly',
                'account_asset_id': self.account_asset.id,
                'account_depreciation_id': self.account_depreciation.id,
                'account_expense_id': self.account_expense.id,
                'journal_id': sale_journal.id,
            })
