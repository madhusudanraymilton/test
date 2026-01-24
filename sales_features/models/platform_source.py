from odoo import models, fields


class PlatformSource(models.Model):
    _name = 'bd.platform.source'
    _description = 'Platform / Lead Source'
    _rec_name = 'name'

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True
    )
