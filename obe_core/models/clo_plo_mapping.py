
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ObeCloPloMapping(models.Model):

    _name = 'obe.clo.plo.mapping'
    _description = 'CLO-PLO Mapping'
    _inherit = ['mail.thread']
    _order = 'clo_id, plo_id'

    clo_id = fields.Many2one(
        'obe.clo',
        string='Course Learning Outcome',
        required=True,
        ondelete='cascade',
        index=True
    )

    state = fields.Selection([
    ('draft', 'Draft'),
    ('confirm', 'Confirmed'),
    ], string='Status', default='draft', required=True)

    plo_id = fields.Many2one(
        'obe.plo',
        string='Program Learning Outcome',
        required=True,
        ondelete='cascade',
        index=True
    )
    strength = fields.Selection([
        ('1', 'Low'),
        ('2', 'Medium'),
        ('3', 'High'),
    ], string='Mapping Strength', required=True, default='2',
       help='Strength of contribution: 1=Low, 2=Medium, 3=High')
    
    strength_value = fields.Integer(
        string='Strength Value',
        compute='_compute_strength_value',
        store=True,
        help='Numeric value for calculations'
    )
    
    justification = fields.Text(
        string='Justification',
        help='Rationale for this mapping and strength level'
    )
    
    evidence_reference = fields.Char(
        string='Evidence Reference',
        help='Reference to supporting evidence (syllabus section, assessment, etc.)'
    )

    course_id = fields.Many2one(
        'obe.course',
        related='clo_id.course_id',
        string='Course',
        store=True
    )

    program_id = fields.Many2one(
        'obe.academic.program',
        related='plo_id.program_id',
        string='Program',
        store=True,
        readonly=True
    )
    offering_id = fields.Many2one(
        'obe.course.offering',
        related='clo_id.offering_id',
        string='Course Offering',
        store=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    def action_draft(self):
        self.ensure_one()
        if self.state != 'draft':
            self.state = 'draft'

    def action_confirm(self):
        self.ensure_one()
        if self.state != 'confirm':
            self.state = 'confirm'
    

    @api.depends('strength')
    def _compute_strength_value(self):
        """Convert strength selection to numeric value"""
        for record in self:
            record.strength_value = int(record.strength) if record.strength else 0

    # @api.constrains('clo_id', 'plo_id')
    # def _check_same_program(self):
    #     """Validate that CLO's course belongs to PLO's program"""
    #     for record in self:
    #         course_programs = record.clo_id.course_id.program_ids
    #         if record.plo_id.program_id not in course_programs:
    #             raise ValidationError(
    #                 _('The course %s is not part of the program %s. '
    #                   'CLO can only be mapped to PLOs from programs offering this course.') %
    #                 (record.clo_id.course_id.code, record.plo_id.program_id.code)
    #             )

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.clo_id.name} → {record.plo_id.name} (Strength: {record.strength})"
            result.append((record.id, name))
        return result

    @api.model
    def create(self, vals):
        """Update many2many on create"""
        mapping = super().create(vals)
        # Update the many2many relationship
        mapping.clo_id.write({'plo_ids': [(4, mapping.plo_id.id)]})
        return mapping

    def unlink(self):
        """Update many2many on delete"""
        for mapping in self:
            mapping.clo_id.write({'plo_ids': [(3, mapping.plo_id.id)]})
        return super().unlink()


class ObeCloPloMappingWizard(models.TransientModel):
    """Wizard for bulk CLO-PLO mapping"""
    _name = 'obe.clo.plo.mapping.wizard'
    _description = 'CLO-PLO Mapping Wizard'

    clo_id = fields.Many2one(
        'obe.clo',
        string='Course Learning Outcome',
        required=True
    )
    course_id = fields.Many2one(
        'obe.course',
        related='clo_id.course_id',
        string='Course'
    )
    plo_ids = fields.Many2many(
        'obe.plo',
        string='Program Learning Outcomes',
        help='Select PLOs to map to this CLO'
    )
    default_strength = fields.Selection([
        ('1', 'Low (1)'),
        ('2', 'Medium (2)'),
        ('3', 'High (3)'),
    ], string='Default Strength', default='2', required=True)
    
    justification = fields.Text(
        string='Justification',
        help='Common justification for all mappings'
    )

    @api.onchange('clo_id')
    def _onchange_clo_id(self):
        """Filter PLOs based on course programs"""
        if self.clo_id and self.clo_id.course_id:
            program_ids = self.clo_id.course_id.program_ids.ids
            return {
                'domain': {
                    'plo_ids': [('program_id', 'in', program_ids)]
                }
            }

    def action_create_mappings(self):
        """Create mappings for selected PLOs"""
        self.ensure_one()
        
        if not self.plo_ids:
            raise ValidationError(_('Please select at least one PLO.'))
        
        Mapping = self.env['obe.clo.plo.mapping']
        created_count = 0
        
        for plo in self.plo_ids:
            # Check if mapping already exists
            existing = Mapping.search([
                ('clo_id', '=', self.clo_id.id),
                ('plo_id', '=', plo.id)
            ])
            
            if not existing:
                Mapping.create({
                    'clo_id': self.clo_id.id,
                    'plo_id': plo.id,
                    'strength': self.default_strength,
                    'justification': self.justification,
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