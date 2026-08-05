from odoo import models, fields, api


class VacEventLeadStatus(models.Model):
    _name = 'vac.event.lead.status'
    _description = 'VAC Event Lead Status'
    _order = 'name'

    name = fields.Char(
        string='Status Name',
        required=True,
        translate=True,
        help='Name of the lead status (e.g., Active, Inactive, Blacklisted, Customer)'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this status'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, it will hide the status without removing it'
    )
    
    color = fields.Integer(
        string='Color Index',
        default=0,
        help='Color indicator for the status'
    )
    
    # Status type flags (optional for business logic)
    is_blacklisted = fields.Boolean(
        string='Is Blacklisted',
        default=False,
        help='Marks this status as blacklisted (no communication allowed)'
    )
    
    is_customer = fields.Boolean(
        string='Is Customer',
        default=False,
        help='Marks this status as converted customer'
    )
    
    # Lead count with this status
    lead_count = fields.Integer(
        string='Leads',
        compute='_compute_lead_count',
        help='Number of leads with this status'
    )
    
    def _compute_lead_count(self):
        """Count leads with this status"""
        for status in self:
            status.lead_count = self.env['vac.event.lead'].search_count([
                ('status_id', '=', status.id)
            ])