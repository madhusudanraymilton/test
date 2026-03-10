# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo import fields
from dateutil.relativedelta import relativedelta
from unittest.mock import patch
from .common import AssetTestCommon


@tagged('post_install', '-at_install', 'asset_depreciation')
class TestDepreciation(AssetTestCommon):

    def test_straight_line_schedule_amounts(self):
        """Straight-line: total of all lines = purchase_price."""
        asset = self._register_asset(serial='SN-SLM-001', purchase_price=36000.0)
        lines = asset.depreciation_line_ids.sorted('sequence')

        self.assertEqual(len(lines), 36)
        total = sum(lines.mapped('amount'))
        self.assertAlmostEqual(total, 36000.0, places=2)

        # Monthly amount should be 1000
        for line in lines[:-1]:  # all but last
            self.assertAlmostEqual(line.amount, 1000.0, places=2)

    def test_straight_line_remaining_value_decreases(self):
        """Straight-line: remaining_value decreases monotonically."""
        asset = self._register_asset(serial='SN-SLM-REM-001', purchase_price=12000.0)
        lines = asset.depreciation_line_ids.sorted('sequence')
        previous = 12000.0
        for line in lines:
            self.assertLessEqual(line.remaining_value, previous)
            previous = line.remaining_value
        # Final remaining value should be 0 (or near 0) for 0% non-depreciable
        self.assertAlmostEqual(lines[-1].remaining_value, 0.0, places=2)

    def test_declining_balance_schedule(self):
        """Declining balance: total depreciated converges toward depreciable amount."""
        cat_db = self.env['asset.category'].create({
            'name': 'DB Category Test',
            'depreciation_method': 'declining',
            'duration_months': 24,
            'computation_method': 'monthly',
            'non_depreciable_pct': 10.0,
            'account_asset_id': self.account_asset.id,
            'account_depreciation_id': self.account_depreciation.id,
            'account_expense_id': self.account_expense.id,
            'journal_id': self.journal.id,
        })
        lot = self._create_lot('SN-DB-001')
        self._add_to_inventory(lot)
        wizard = self.env['asset.register.wizard'].create({
            'lot_id': lot.id,
            'category_id': cat_db.id,
            'purchase_price': 24000.0,
            'source_location_id': self.stock_location.id,
        })
        result = wizard.action_register()
        asset = self.env['asset.asset'].browse(result['res_id'])

        lines = asset.depreciation_line_ids.sorted('sequence')
        self.assertEqual(len(lines), 24)
        # Each line's amount must be > 0
        for line in lines:
            self.assertGreater(line.amount, 0.0)
        # Book value must not go negative
        for line in lines:
            self.assertGreaterEqual(line.remaining_value, 0.0)

    def test_cron_posts_due_lines(self):
        """Cron posts all unposted lines with depreciation_date <= today."""
        asset = self._register_asset(serial='SN-CRON-001', purchase_price=12000.0)

        # Force the first 3 lines' dates to be in the past
        lines = asset.depreciation_line_ids.sorted('sequence')[:3]
        past_date = fields.Date.today() - relativedelta(months=1)
        for line in lines:
            # Direct DB write to bypass any ORM checks
            self.env.cr.execute(
                'UPDATE asset_depreciation_line SET depreciation_date = %s WHERE id = %s',
                (past_date, line.id)
            )
        self.env.cache.invalidate()

        self.env['asset.depreciation.line']._cron_post_depreciation()

        posted = asset.depreciation_line_ids.filtered('move_posted_check')
        self.assertEqual(len(posted), 3)

    def test_cron_skips_scrapped_assets(self):
        """Cron does not post depreciation for scrapped assets."""
        asset = self._register_asset(serial='SN-CRON-SCRAP-001', purchase_price=6000.0)

        lines = asset.depreciation_line_ids.sorted('sequence')[:1]
        past_date = fields.Date.today() - relativedelta(days=1)
        self.env.cr.execute(
            'UPDATE asset_depreciation_line SET depreciation_date = %s WHERE id = %s',
            (past_date, lines[0].id)
        )
        self.env.cache.invalidate()

        asset.action_scrap()
        self.assertEqual(asset.state, 'scrapped')

        self.env['asset.depreciation.line']._cron_post_depreciation()
        self.assertFalse(lines[0].move_posted_check)

    def test_savepoint_rollback_on_failure(self):
        """A failed depreciation posting does not affect other lines."""
        asset1 = self._register_asset(serial='SN-SAVE-001', purchase_price=3600.0)
        asset2 = self._register_asset(serial='SN-SAVE-002', purchase_price=3600.0)

        past = fields.Date.today() - relativedelta(months=1)
        for a in (asset1, asset2):
            first_line = a.depreciation_line_ids.sorted('sequence')[0]
            self.env.cr.execute(
                'UPDATE asset_depreciation_line SET depreciation_date = %s WHERE id = %s',
                (past, first_line.id)
            )
        self.env.cache.invalidate()

        # Break asset1's category journal to cause posting failure
        asset1.category_id.write({'journal_id': False})

        with self.assertLogs('odoo.addons.custom_asset_management', level='ERROR'):
            self.env['asset.depreciation.line']._cron_post_depreciation()

        # asset2's line should still be posted
        line2 = asset2.depreciation_line_ids.sorted('sequence')[0]
        self.assertTrue(line2.move_posted_check)
