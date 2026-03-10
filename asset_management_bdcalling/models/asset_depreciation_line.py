# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AssetDepreciationLine(models.Model):
    _name = 'asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'asset_id, sequence'

    asset_id = fields.Many2one(
        'asset.asset',
        string='Asset',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', required=True)
    depreciation_date = fields.Date(
        string='Depreciation Date',
        required=True,
        index=True,
    )
    amount = fields.Monetary(
        string='Depreciation Amount',
        currency_field='currency_id',
        required=True,
    )
    remaining_value = fields.Monetary(
        string='Book Value After',
        currency_field='currency_id',
        required=True,
    )
    depreciated_value = fields.Monetary(
        string='Cumulative Depreciation',
        currency_field='currency_id',
        required=True,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        ondelete='set null',
    )
    move_check = fields.Boolean(
        string='Journal Entry Created',
        default=False,
        index=True,
    )
    move_posted_check = fields.Boolean(
        string='Journal Entry Posted',
        default=False,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    def _post_depreciation_move(self):
        """
        Create and post a double-entry journal entry for this depreciation line.
        DR: Depreciation Expense Account
        CR: Accumulated Depreciation Account
        """
        self.ensure_one()
        asset = self.asset_id
        category = asset.category_id

        if self.move_posted_check:
            raise UserError(_(
                'Depreciation line %s for asset %s is already posted.'
            ) % (self.sequence, asset.code))

        move_vals = {
            'journal_id': category.journal_id.id,
            'date': self.depreciation_date,
            'ref': _('Depreciation %s - Line %s') % (asset.code, self.sequence),
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'account_id': category.account_expense_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'name': _('%s Depreciation') % asset.name,
                    'currency_id': self.currency_id.id,
                }),
                (0, 0, {
                    'account_id': category.account_depreciation_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'name': _('%s Accumulated Depreciation') % asset.name,
                    'currency_id': self.currency_id.id,
                }),
            ],
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.write({
            'move_id': move.id,
            'move_check': True,
            'move_posted_check': True,
        })

        asset._log_history(
            event_type='depreciate',
            old_state=asset.state,
            new_state=asset.state,
            description=_('Depreciation line %s posted — amount: %s') % (
                self.sequence, self.amount,
            ),
            metadata={
                'move_id': move.id,
                'amount': self.amount,
                'sequence': self.sequence,
            },
        )
        return move

    @api.model
    def _cron_post_depreciation(self):
        """
        Monthly cron: post all unposted depreciation lines due up to today.
        Each line is processed in its own savepoint for rollback isolation.
        """
        today = fields.Date.today()
        lines = self.search([
            ('move_check', '=', False),
            ('depreciation_date', '<=', today),
            ('asset_id.state', 'in', ['available', 'assigned']),
        ])

        _logger.info('AMS Depreciation Cron: processing %d lines', len(lines))
        failed = []

        for line in lines:
            try:
                with self.env.cr.savepoint():
                    line._post_depreciation_move()
            except Exception as exc:
                failed.append((line.id, str(exc)))
                _logger.error(
                    'AMS: Depreciation failed for asset %s line %s: %s',
                    line.asset_id.code,
                    line.sequence,
                    exc,
                )

        if failed:
            _logger.warning(
                'AMS Depreciation Cron completed with %d failures: %s',
                len(failed), failed,
            )
        else:
            _logger.info('AMS Depreciation Cron completed successfully.')
