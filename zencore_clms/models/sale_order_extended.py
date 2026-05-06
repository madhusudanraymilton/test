from odoo import models, fields

class SaleOrderExtended(models.Model):
    _inherit = 'sale.order'

    clm_state = fields.Selection([
        ('pi', 'Proforma Invoice'),
        ('bucket1', 'Bucket 1'),
        ('bucket2', 'Bucket 2'),
        ('bucket3', 'Bucket 3'),
        ('bucket4', 'Bucket 4'),
        ('paid', 'Paid'),
    ], default='pi', tracking=True)
