from odoo import models, fields, api   

class AccountMoveExtended(models.Model):
    _inherit = 'account.move'

    country_id = fields.Many2one('res.country', related="partner_id.country_id", store=True,string="Country", index=True)

    state_id = fields.Many2one(
        'res.country.state',
        related="partner_id.state_id",
        store=True,
        string="Division",
        # domain="[('thana_id','=',thana_id)]",
        index=True
    )

    district_id = fields.Many2one(
        'res.district',
        related="partner_id.district_id",
        store=True,
        string="District",
        # domain="[('thana_id','=',thana_id)]",
        index=True
    )

    thana_id = fields.Many2one(
        'res.thana',
        related="partner_id.thana_id",
        store=True,
        string="Thana",
        # domain="[('thana_id','=',thana_id)]",
        index=True
    )

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.country_id = self.partner_id.country_id
            self.state_id = self.partner_id.state_id
            self.district_id = self.partner_id.district_id
            self.thana_id = self.partner_id.thana_id

    