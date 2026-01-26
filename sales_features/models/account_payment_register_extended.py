from odoo import models, api, fields

class AccountPaymentRegisterExtended(models.TransientModel):
    _inherit = 'account.payment.register'

    # profile_id = fields.Many2one('bd.profile.name', string="Profile")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return res

        # These are account.move.line ids
        move_lines = self.env['account.move.line'].browse(active_ids).exists()
        if not move_lines:
            return res

        # Take the first move line and go to its move
        move = move_lines[0].move_id

        # Now safely read profile → journal
        if move.profile_id and move.profile_id.journal_id:
            res['journal_id'] = move.profile_id.journal_id.id

        return res
