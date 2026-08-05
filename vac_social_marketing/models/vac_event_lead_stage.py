from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VacEventLeadStage(models.Model):
    _name = 'vac.event.lead.stage'
    _description = 'VAC Event Lead Stage'
    _order = 'sequence, name'

    name = fields.Char(
        string='Stage Name',
        required=True,
        translate=True,
        help='Name of the lead stage (e.g., New Lead, Contacted, Converted)'
    )
    
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of this stage'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of stages in the kanban view'
    )
    
    fold = fields.Boolean(
        string='Folded in Kanban',
        default=False,
        help='This stage is folded in the kanban view when there are no records'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, it will hide the stage without removing it'
    )
    
    color = fields.Integer(
        string='Color Index',
        default=0,
        help='Color for kanban view'
    )
    
    is_signed = fields.Boolean(
        string='Is Signed Stage',
        default=False,
        help='Mark this stage as the signed stage. Only one stage can be marked as signed.'
    )
    
    # Lead count in this stage
    lead_count = fields.Integer(
        string='Leads',
        compute='_compute_lead_count',
        help='Number of leads in this stage'
    )
    
    def _compute_lead_count(self):
        """Count leads in this stage"""
        for stage in self:
            stage.lead_count = self.env['vac.event.lead'].search_count([
                ('stage_id', '=', stage.id)
            ])
    
    @api.model_create_multi
    def create(self, vals_list):
        """Check on create"""
        for vals in vals_list:
            if vals.get('is_signed'):
                existing = self.search([('is_signed', '=', True)], limit=1)
                if existing:
                    raise UserError(_(
                        '⚠️ Only One Signed Stage Allowed!\n\n'
                        '"%s" is already marked as the signed stage.\n\n'
                        'Please uncheck "%s" first before marking another stage as signed.'
                    ) % (existing.name, existing.name))
        
        return super(VacEventLeadStage, self).create(vals_list)
    
    def write(self, vals):
        """Check on update - this triggers the popup"""
        if 'is_signed' in vals and vals.get('is_signed'):
            # Check each record in the recordset
            for record in self:
                # Look for other stages that are already signed
                existing = self.search([
                    ('is_signed', '=', True),
                    ('id', '!=', record.id)
                ], limit=1)
                
                if existing:
                    raise UserError(_(
                        '⚠️ Only One Signed Stage Allowed!\n\n'
                        '"%s" is already marked as the signed stage.\n\n'
                        'Please uncheck "%s" first, then you can mark "%s" as signed.'
                    ) % (existing.name, existing.name, record.name))
        
        return super(VacEventLeadStage, self).write(vals)