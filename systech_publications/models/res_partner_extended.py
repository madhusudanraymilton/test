from odoo import models, fields, api

class ResPartnerExtended(models.Model):
    _inherit = 'res.partner'

    thana_id = fields.Many2one(
        'res.thana',
        string='Thana'
    )

    district_id = fields.Many2one(
        'res.district',
        string='District',
      #  domain="[('thana_id', '=', thana_id)]"
    )

    @api.onchange('thana_id')
    def _onchange_thana_id(self):
        if self.thana_id:
            self.district_id = self.thana_id.district_id
            self.state_id = self.thana_id.state_id
            self.country_id = self.thana_id.country_id

class ResThana(models.Model):
    _name = 'res.thana'
    _description = 'Thana'

    name = fields.Char(string='Thana Name', required=True)
    district_id = fields.Many2one(
        'res.district',
        string='District',
        # domain="[('thana_id', '=', thana_id)]",
        required=True
    )
    state_id = fields.Many2one(
        'res.country.state',
        related="district_id.state_id",
        string='Division',
        placeholder='Division',
        # domain="[('thana_id', '=', thana_id)]",
        store=True
    )
    country_id = fields.Many2one(
        'res.country',
        related="district_id.country_id",
        string='Country',
        placeholder='Country',
        store=True
    )
    @api.onchange('district_id')
    def _onchange_district_id(self):
        if self.district_id:
            self.state_id = self.district_id.state_id
            self.country_id = self.district_id.country_id

class ResDistrict(models.Model):
    _name = 'res.district'
    _description = 'District'

    name = fields.Char(string='District Name', required=True)
    state_id = fields.Many2one(
        'res.country.state',
        string='Division',
        # domain="[('thana_id', '=', thana_id)]",
        required=True
    )
    country_id = fields.Many2one(
        'res.country',
        related="state_id.country_id",
        string='Country',
        store=True
    )

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id:
            self.country_id = self.state_id.country_id
    