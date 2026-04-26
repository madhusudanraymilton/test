from odoo import models, fields


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    branch_id = fields.Many2one('acs.branch', string="Branch", index=True)
    _depends = {'account.move': ['branch_id'],}

    def _select(self):
        return super()._select() + ", move.branch_id as branch_id"
