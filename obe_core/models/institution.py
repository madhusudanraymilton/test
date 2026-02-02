from odoo import models, fields, api

class Institution(models.Model):
    _name = 'obe.core.institution'
    _description = 'Educational Institution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Institution Name', required=True)
    code = fields.Char(string='Institution Code', required=True, unique=True)
    vision = fields.Text(string='Vision Statement', max_length=2000)
    mission = fields.Text(string='Mission Statement', max_length=2000)
    vision_effective_date = fields.Date(string='Vision Effective Date')
    mission_effective_date = fields.Date(string='Mission Effective Date')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('published', 'Published')
    ], string='Status', default='draft')
    
    # Accreditation
    # accreditation_body = fields.Selection([
    #     ('baete', 'BAETE'),
    #     ('abet', 'ABET'),
    #     ('nba', 'NBA'),
    #     ('other', 'Other')
    # ], string='Accreditation Body')
    # accreditation_id = fields.Char(string='Accreditation ID')
    
    # Contact Information
    address = fields.Text(string='Address')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    website = fields.Char(string='Website')
    
    # Related Records
    # program_ids = fields.One2many('obe.academic.program', 'institution_id', string='Academic Programs')
    # department_ids = fields.One2many('obe.department', 'institution_id', string='Departments')
    
    # Audit Fields
    active = fields.Boolean(string='Active', default=True)
    version = fields.Integer(string='Version', default=1)
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Institution code must be unique!'),
    ]
    
    @api.model
    def create(self, vals):
        if 'code' in vals:
            vals['code'] = vals['code'].upper()
        return super(Institution, self).create(vals)
    
    def write(self, vals):
        if 'code' in vals:
            vals['code'] = vals['code'].upper()
        return super(Institution, self).write(vals)