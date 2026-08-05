from odoo import models, fields


class VacBranchService(models.Model):
    _name = 'vac.branch.service'
    _description = 'VAC Branch / Service'
    _order = 'name'

    name = fields.Char(
        string='Branch / Service Name',
        required=True,
        help='Name of the branch or service (e.g., Dhaka Branch, Diabetes Care)'
    )
    
    code = fields.Char(
        string='Code',
        help='Short code for the branch/service'
    )
    
    description = fields.Text(
        string='Description',
        help='Details about this branch or service'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Archive instead of deleting'
    )
    
    # Type of entry
    type = fields.Selection([
        ('branch', 'Branch'),
        ('service', 'Service'),
        ('both', 'Branch & Service')
    ], string='Type', default='both', required=True)