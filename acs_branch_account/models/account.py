# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_branch_id(self):
        branch_id = False
        if self.env.user.branch_id:
            if self.env.user.acs_main_active_branch_id:
                branch_id = self.env.user.acs_main_active_branch_id
            else:
                branch_id = self.env.user.acs_main_active_branch_id or self.env.user.branch_id.id
        return branch_id

    branch_id = fields.Many2one('acs.branch', string="Branch", readonly=True,
        states={'draft': [('readonly', False)]}, default=_get_branch_id)

    @api.onchange('branch_id')
    def onchange_branch(self):
        if self.branch_id:
            self.journal_id = self.branch_id.journal_id.id


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    branch_id = fields.Many2one('acs.branch', string="Branch", related="move_id.branch_id", store=True)