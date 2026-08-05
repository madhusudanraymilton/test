from odoo import fields, models


class VacSponsor(models.Model):
    _name        = 'vac.sponsor'
    _description = 'VAC Sponsor'
    _order       = 'sequence, name'

    name     = fields.Char(string='Sponsor Name', required=True)
    sequence = fields.Integer(default=10)
    active   = fields.Boolean(default=True)

    # computed: events linked to this sponsor
    event_count = fields.Integer(
        string='Events',
        compute='_compute_event_count',
    )

    def _compute_event_count(self):
        for sponsor in self:
            sponsor.event_count = self.env['vac.event'].search_count(
                [('sponsor_id', '=', sponsor.id)]
            )
