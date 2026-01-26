from odoo import models, fields, api, _ 

class AccountPaymentExtended(models.Model):
    _inherit = 'account.payment'

    profile_id = fields.Many2one(
        'bd.profile.name',
        string="Profile",
        tracking=True
    )

