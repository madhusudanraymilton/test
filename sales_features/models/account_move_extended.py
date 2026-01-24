from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountMoveExtended(models.Model):
    _inherit = 'account.move'

    profile_id = fields.Many2one('bd.profile.name', string="Profile")



    # @api.onchange("partner_id")
    # def get_profile(self):
        

    
    @api.onchange('profile_id')
    def _onchange_profile_id(self):
        if not self.profile_id:
            return

        income_account = self.profile_id.income_account
        receivable_account = self.profile_id.receivable_account

        if income_account.internal_group in ('receivable', 'payable'):
            raise ValidationError(
                "Profile income account must be an Income or Expense account, "
                "not a Receivable/Payable account."
            )
        
        # Validate receivable account
        if receivable_account and receivable_account.account_type != 'asset_receivable':
            raise ValidationError(
                "Profile receivable account must be a Receivable account type."
            )
        


        for line in self.invoice_line_ids:
            line.account_id = income_account

        
        if receivable_account:
            for line in self.line_ids.filtered(lambda l: l.display_type == 'payment_term'):
                line.account_id = receivable_account
        

class AccountMoveLineExtended(models.Model):
    _inherit = 'account.move.line'


    account_id = fields.Many2one(
        'account.account',
        domain="[('id', 'in', profile_id.allowed_account)]"
    )
    

