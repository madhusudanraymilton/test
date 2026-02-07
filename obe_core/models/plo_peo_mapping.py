# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ObePloPeoMapping(models.Model):
    """PLO to PEO Mapping with Relationship Strength"""
    _name = 'obe.plo.peo.mapping'
    _description = 'PLO-PEO Mapping'
    _inherit = ['mail.thread']
    _order = 'plo_id, peo_id'

    plo_id = fields.Many2one(
        'obe.plo',
        string='Program Learning Outcome',
        required=True,
        ondelete='cascade',
        index=True
    )

    plo_ids = fields.Many2many(
        'obe.plo',
        'plo_peo_rel',
        'peo_id',
        'plo_id',
        string='Related PLOs',
        help='PLOs that contribute to this PEO'
    )

    peo_id = fields.Many2one(
        'obe.peo',
        string='Program Educational Objective',
        required=True,
        ondelete='cascade',
        index=True
    )
    strength = fields.Selection([
        ('1', 'Low (1)'),
        ('2', 'Medium (2)'),
        ('3', 'High (3)'),
    ], string='Relationship Strength', required=True, default='2',
       help='Strength of contribution: 1=Low, 2=Medium, 3=High')
    
    strength_value = fields.Integer(
        string='Strength Value',
        compute='_compute_strength_value',
        store=True,
        help='Numeric value for calculations'
    )
    
    rationale = fields.Text(
        string='Supporting Rationale',
        help='Explanation of how this PLO contributes to the PEO'
    )
    
    # Related fields for easier filtering
    program_id = fields.Many2one(
        'obe.academic.program',
        related='plo_id.program_id',
        string='Program',
        store=True,
        readonly=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    _sql_constraints = [
        ('unique_plo_peo', 
         'unique(plo_id, peo_id)', 
         'Mapping between this PLO and PEO already exists!'),
    ]

    @api.depends('strength')
    def _compute_strength_value(self):
        """Convert strength selection to numeric value"""
        for record in self:
            record.strength_value = int(record.strength) if record.strength else 0

    # @api.constrains('plo_id', 'peo_id')
    # def _check_same_program(self):
    #     """Validate that PLO and PEO belong to the same program"""
    #     for record in self:
    #         if record.plo_id.program_id != record.peo_id.program_id:
    #             raise ValidationError(
    #                 _('PLO and PEO must belong to the same program. '
    #                   'PLO is from %s but PEO is from %s.') %
    #                 (record.plo_id.program_id.code, record.peo_id.program_id.code)
    #             )

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.plo_id.name} → {record.peo_id.name} (Strength: {record.strength})"
            result.append((record.id, name))
        return result

    @api.model
    def create(self, vals):
        """Update many2many on create"""
        mapping = super().create(vals)
        # Update the many2many relationships
        mapping.plo_id.write({'peo_ids': [(4, mapping.peo_id.id)]})
        mapping.peo_id.write({'plo_ids': [(4, mapping.plo_id.id)]})
        return mapping

    def unlink(self):
        """Update many2many on delete"""
        for mapping in self:
            mapping.plo_id.write({'peo_ids': [(3, mapping.peo_id.id)]})
            mapping.peo_id.write({'plo_ids': [(3, mapping.plo_id.id)]})
        return super().unlink()


class ObePloPeoMappingWizard(models.TransientModel):
    """Wizard for bulk PLO-PEO mapping"""
    _name = 'obe.plo.peo.mapping.wizard'
    _description = 'PLO-PEO Mapping Wizard'

    plo_id = fields.Many2one(
        'obe.plo',
        string='Program Learning Outcome',
        required=True
    )
    program_id = fields.Many2one(
        'obe.academic.program',
        related='plo_id.program_id',
        string='Program',
        readonly=True
    )
    peo_ids = fields.Many2many(
        'obe.peo',
        string='Program Educational Objectives',
        help='Select PEOs that this PLO contributes to'
    )
    default_strength = fields.Selection([
        ('1', 'Low (1)'),
        ('2', 'Medium (2)'),
        ('3', 'High (3)'),
    ], string='Default Strength', default='2', required=True)
    
    rationale = fields.Text(
        string='Rationale',
        help='Common rationale for all mappings'
    )

    @api.onchange('plo_id')
    def _onchange_plo_id(self):
        """Filter PEOs to same program as PLO"""
        if self.plo_id and self.plo_id.program_id:
            return {
                'domain': {
                    'peo_ids': [('program_id', '=', self.plo_id.program_id.id)]
                }
            }

    def action_create_mappings(self):
        """Create mappings for selected PEOs"""
        self.ensure_one()
        
        if not self.peo_ids:
            raise ValidationError(_('Please select at least one PEO.'))
        
        Mapping = self.env['obe.plo.peo.mapping']
        created_count = 0
        
        for peo in self.peo_ids:
            # Check if mapping already exists
            existing = Mapping.search([
                ('plo_id', '=', self.plo_id.id),
                ('peo_id', '=', peo.id)
            ])
            
            if not existing:
                Mapping.create({
                    'plo_id': self.plo_id.id,
                    'peo_id': peo.id,
                    'strength': self.default_strength,
                    'rationale': self.rationale,
                })
                created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%s mapping(s) created successfully.') % created_count,
                'type': 'success',
                'sticky': False,
            }
        }