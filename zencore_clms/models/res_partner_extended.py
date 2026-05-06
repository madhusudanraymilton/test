from odoo import models, fields

class ResPartnerExtended(models.Model):
    _inherit = 'res.partner'

    clm_bucket_1_limit = fields.Char(string='Bucket 1 limit') 
    clm_bucket_2_limit = fields.Char(string='Bucket 2 limit') 
    clm_bucket_3_limit = fields.Char(string='Bucket 3 limit') 
    clm_bucket_4_limit = fields.Char(string='Bucket 4 limit')

    clm_bucket_1_balance = fields.Float(string='Bucket 1 balance')
    clm_bucket_2_balance = fields.Float(string='Bucket 2 balance')
    clm_bucket_3_balance = fields.Float(string='Bucket 3 balance')
    clm_bucket_4_balance = fields.Float(string='Bucket 4 balance')

