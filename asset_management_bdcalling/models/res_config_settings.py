# # -*- coding: utf-8 -*-
# from odoo import fields, models


# class ResConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'

#     asset_location_id = fields.Many2one(
#         'stock.location',
#         string='Default Asset Location',
#         related='company_id.asset_location_id',
#         readonly=False,
#         domain="[('usage', '=', 'internal')]",
#         help='Default stock location where registered assets are moved to.',
#     )
#     auto_return_on_employee_archive = fields.Boolean(
#         string='Auto-Return Assets on Employee Archive',
#         related='company_id.auto_return_on_employee_archive',
#         readonly=False,
#         help='Automatically return all assets when an employee is archived.',
#     )
#     asset_assign_date_future_allowed = fields.Boolean(
#         string='Allow Future Assignment Dates',
#         related='company_id.asset_assign_date_future_allowed',
#         readonly=False,
#         help='Allow setting an assignment date in the future.',
#     )


# class ResCompany(models.Model):
#     _inherit = 'res.company'

#     asset_location_id = fields.Many2one(
#         'stock.location',
#         string='Default Asset Location',
#         domain="[('usage', '=', 'internal')]",
#     )
#     auto_return_on_employee_archive = fields.Boolean(
#         string='Auto-Return Assets on Employee Archive',
#         default=False,
#     )
#     asset_assign_date_future_allowed = fields.Boolean(
#         string='Allow Future Assignment Dates',
#         default=False,
#     )

# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Asset Location ────────────────────────────────────────────────────────
    asset_location_id = fields.Many2one(
        'stock.location',
        string='Default Asset Location',
        related='company_id.asset_location_id',
        readonly=False,
        domain="[('usage', '=', 'internal')]",
        help='Default stock location where registered assets are moved to.',
    )

    # ── Auto-Return on Employee Archive ───────────────────────────────────────
    auto_return_on_employee_archive = fields.Boolean(
        string='Auto-Return Assets on Employee Archive',
        related='company_id.auto_return_on_employee_archive',
        readonly=False,
        help=(
            'When an employee is archived, automatically mark all their '
            'assigned assets as returned and set them back to Available.'
        ),
    )

    # ── Future Assignment Dates ───────────────────────────────────────────────
    asset_assign_date_future_allowed = fields.Boolean(
        string='Allow Future Assignment Dates',
        related='company_id.asset_assign_date_future_allowed',
        readonly=False,
        help='Allow users to set an assignment date in the future.',
    )

    # ── Default Assignment Condition ──────────────────────────────────────────
    asset_default_assign_condition = fields.Selection(
        related='company_id.asset_default_assign_condition',
        readonly=False,
    )

    # ── Require Return Notes ──────────────────────────────────────────────────
    asset_require_return_notes = fields.Boolean(
        string='Require Notes on Asset Return',
        related='company_id.asset_require_return_notes',
        readonly=False,
        help='Force the user to enter notes when returning an asset.',
    )

    # ── Notify on Assignment ──────────────────────────────────────────────────
    asset_notify_employee_on_assign = fields.Boolean(
        string='Notify Employee on Assignment',
        related='company_id.asset_notify_employee_on_assign',
        readonly=False,
        help='Send an email notification to the employee when an asset is assigned to them.',
    )

    # ── Low Value Threshold ───────────────────────────────────────────────────
    asset_low_value_threshold = fields.Monetary(
        string='Low-Value Asset Threshold',
        related='company_id.asset_low_value_threshold',
        readonly=False,
        currency_field='currency_id',
        help=(
            'Assets with a purchase price below this amount are flagged '
            'as low-value in reports and the dashboard.'
        ),
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True,
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ── Inventory ─────────────────────────────────────────────────────────────
    asset_location_id = fields.Many2one(
        'stock.location',
        string='Default Asset Location',
        domain="[('usage', '=', 'internal')]",
    )

    # ── Lifecycle Automation ──────────────────────────────────────────────────
    auto_return_on_employee_archive = fields.Boolean(
        string='Auto-Return Assets on Employee Archive',
        default=False,
    )
    asset_assign_date_future_allowed = fields.Boolean(
        string='Allow Future Assignment Dates',
        default=False,
    )

    # ── Assignment Defaults ───────────────────────────────────────────────────
    asset_default_assign_condition = fields.Selection(
        selection=[
            ('new',  'New'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        string='Default Assignment Condition',
        default='good',
        help='Pre-selected condition when opening the Assign Asset wizard.',
    )
    asset_require_return_notes = fields.Boolean(
        string='Require Notes on Asset Return',
        default=False,
    )

    # ── Notifications ─────────────────────────────────────────────────────────
    asset_notify_employee_on_assign = fields.Boolean(
        string='Notify Employee on Assignment',
        default=False,
    )

    # ── Financials ────────────────────────────────────────────────────────────
    asset_low_value_threshold = fields.Monetary(
        string='Low-Value Asset Threshold',
        currency_field='currency_id',
        default=0.0,
    )