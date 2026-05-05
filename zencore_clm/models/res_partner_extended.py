from odoo import models, fields

class ResPartnerExtended(models.Model):
    _inherit = 'res.partner'

    clm_bucket_1_l = fields.Char(string='Bucket 1') 
    clm_bucket_2_l = fields.Char(string='Bucket 2') 
    clm_bucket_3_l = fields.Char(string='Bucket 3') 
    clm_bucket_4_l = fields.Char(string='Bucket 4')

    clm_bucket_1_b = fields.Float(string='Bucket 1')
    clm_bucket_2_b = fields.Float(string='Bucket 2')
    clm_bucket_3_b = fields.Float(string='Bucket 3')
    clm_bucket_4_b = fields.Float(string='Bucket 4')

    