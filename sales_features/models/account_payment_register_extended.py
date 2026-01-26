from odoo import models, api, fields

class AccountPaymentRegisterExtended(models.TransientModel):
    _inherit = 'account.payment.register'

    profile_id = fields.Many2one('bd.profile.name', string="Profile")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return res

        active_model = self.env.context.get('active_model')
        
        # Handle if called from account.move directly
        if active_model == 'account.move':
            moves = self.env['account.move'].browse(active_ids).exists()
            if moves:
                move = moves[0]
                if move.profile_id:
                    res['profile_id'] = move.profile_id.id
                    if move.profile_id.journal_id:
                        res['journal_id'] = move.profile_id.journal_id.id
        
        # Handle if called from account.move.line
        elif active_model == 'account.move.line':
            move_lines = self.env['account.move.line'].browse(active_ids).exists()
            if move_lines:
                move = move_lines[0].move_id
                if move.profile_id:
                    res['profile_id'] = move.profile_id.id
                    if move.profile_id.journal_id:
                        res['journal_id'] = move.profile_id.journal_id.id

        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        """Override to add profile_id to payment values"""
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        
        # Add profile_id to the payment
        if self.profile_id:
            payment_vals['profile_id'] = self.profile_id.id
        
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        """Override to add profile_id to payment values (alternative method)"""
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        
        # Add profile_id to the payment
        if self.profile_id:
            payment_vals['profile_id'] = self.profile_id.id
        
        return payment_vals