from odoo import models, fields


class ProfileName(models.Model):
    _name = 'bd.profile.name'
    _description = 'Profile Name'
    _rec_name = 'name'

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True
    )

    platform_source_id = fields.Many2one(
        'bd.platform.source',
        string="Platform Source"
    )

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company
    )

    income_account = fields.Many2one(
        'account.account',
        string="Income Account",
        domain=[('account_type', '=', 'income')],
        tracking=True
    )

    receivable_account = fields.Many2one(
        'account.account',
        string="Receivable Account",
        domain=[('account_type', '=', 'asset_receivable')],
        tracking=True
    )

    journal_id = fields.Many2one(
        'account.journal',
        string="Journal",
        tracking=True
    )

    allowed_account = fields.Many2many(
        'account.account', 
        string="Allowed Account"
    )
