
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

# # -*- coding: utf-8 -*-

# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError

# class ObeCloPloMapping(models.Model):
#     """CLO to PLO Mapping with Relationship Strength"""
#     _name = 'obe.clo.plo.mapping'
#     _description = 'CLO-PLO Mapping'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _order = 'sequence, clo_id'

#     # Basic Information
#     name = fields.Char(
#         string='Mapping Reference',
#         compute='_compute_name',
#         store=True
#     )
    
#     clo_id = fields.Many2one(
#         'obe.clo',
#         string='Course Learning Outcome',
#         required=True,
#         ondelete='cascade',
#         index=True,
#         tracking=True
#     )
    
#     plo_ids = fields.Many2many(
#         'obe.plo',
#         'clo_plo_mapping_rel',
#         'mapping_id',
#         'plo_id',
#         string='Program Learning Outcomes',
#         help='PLOs that this CLO contributes to'
#     )
    
#     plo_count = fields.Integer(
#         string='PLO Count',
#         compute='_compute_plo_count',
#         store=True
#     )

#     # State Management
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('active', 'Active'),
#         ('archived', 'Archived')
#     ], string='Status', default='draft', required=True, tracking=True)

#     # Strength Configuration
#     strength = fields.Selection([
#         ('1', 'Low (1)'),
#         ('2', 'Medium (2)'),
#         ('3', 'High (3)'),
#     ], string='Mapping Strength', required=True, default='2',
#        help='Strength of contribution: 1=Low, 2=Medium, 3=High',
#        tracking=True)
    
#     strength_value = fields.Integer(
#         string='Strength Value',
#         compute='_compute_strength_value',
#         store=True,
#         help='Numeric value for calculations'
#     )
    
#     # Documentation
#     justification = fields.Text(
#         string='Justification',
#         help='Rationale for this mapping and strength level',
#         tracking=True
#     )
    
#     evidence_reference = fields.Char(
#         string='Evidence Reference',
#         help='Reference to supporting evidence (syllabus section, assessment, etc.)'
#     )

#     # Related Fields
#     course_id = fields.Many2one(
#         'obe.course',
#         related='clo_id.course_id',
#         string='Course',
#         store=True,
#         readonly=True
#     )

#     program_id = fields.Many2one(
#         'obe.academic.program',
#         string='Program',
#         compute='_compute_program_id',
#         store=True,
#         readonly=True
#     )
    
#     institution_id = fields.Many2one(
#         'obe.institution',
#         string='Institution',
#         compute='_compute_institution_id',
#         store=True,
#         readonly=True
#     )
    
#     offering_id = fields.Many2one(
#         'obe.course.offering',
#         related='clo_id.offering_id',
#         string='Course Offering',
#         store=True,
#         readonly=True
#     )
    
#     # Sequencing
#     sequence = fields.Integer(
#         string='Sequence',
#         default=10,
#         help='Display order'
#     )
    
#     # Active Status
#     active = fields.Boolean(
#         string='Active',
#         default=True,
#         tracking=True
#     )
    
#     # Audit Fields
#     created_by = fields.Many2one(
#         'res.users',
#         string='Created By',
#         default=lambda self: self.env.user,
#         readonly=True
#     )
    
#     created_date = fields.Datetime(
#         string='Created Date',
#         default=fields.Datetime.now,
#         readonly=True
#     )
    
#     last_updated_by = fields.Many2one(
#         'res.users',
#         string='Last Updated By',
#         readonly=True
#     )
    
#     last_updated_date = fields.Datetime(
#         string='Last Updated Date',
#         readonly=True
#     )

#     @api.depends('clo_id', 'plo_ids')
#     def _compute_name(self):
#         """Generate mapping reference name"""
#         for record in self:
#             if record.clo_id and record.plo_ids:
#                 plo_names = ', '.join(record.plo_ids.mapped('name'))
#                 record.name = f"{record.clo_id.name} → {plo_names}"
#             elif record.clo_id:
#                 record.name = f"{record.clo_id.name} (No PLOs)"
#             else:
#                 record.name = 'New Mapping'

#     @api.depends('plo_ids')
#     def _compute_plo_count(self):
#         """Count mapped PLOs"""
#         for record in self:
#             record.plo_count = len(record.plo_ids)

#     @api.depends('strength')
#     def _compute_strength_value(self):
#         """Convert strength selection to numeric value"""
#         for record in self:
#             record.strength_value = int(record.strength) if record.strength else 0

#     @api.depends('plo_ids')
#     def _compute_program_id(self):
#         """Compute program from first PLO"""
#         for record in self:
#             if record.plo_ids:
#                 record.program_id = record.plo_ids[0].program_id
#             else:
#                 record.program_id = False

#     @api.depends('clo_id')
#     def _compute_institution_id(self):
#         """Compute institution from CLO"""
#         for record in self:
#             record.institution_id = record.clo_id.institution_id if record.clo_id else False

#     @api.constrains('plo_ids')
#     def _check_plo_mapping(self):
#         """Ensure at least one PLO is mapped when active"""
#         for record in self:
#             if record.state == 'active' and not record.plo_ids:
#                 raise ValidationError(
#                     _('Active mappings must have at least one PLO mapped.')
#                 )

#     def name_get(self):
#         """Custom name display"""
#         result = []
#         for record in self:
#             if record.plo_ids:
#                 plo_names = ', '.join(record.plo_ids.mapped('name')[:3])
#                 if len(record.plo_ids) > 3:
#                     plo_names += f" (+{len(record.plo_ids) - 3} more)"
#                 name = f"{record.clo_id.name} → {plo_names} (Strength: {record.strength})"
#             else:
#                 name = f"{record.clo_id.name} (No PLOs)"
#             result.append((record.id, name))
#         return result

#     def write(self, vals):
#         """Track updates"""
#         vals['last_updated_by'] = self.env.user.id
#         vals['last_updated_date'] = fields.Datetime.now()
#         result = super().write(vals)
        
#         # Update many2many relationships
#         if 'plo_ids' in vals:
#             for mapping in self:
#                 # Update the CLO's plo_ids field
#                 if mapping.clo_id:
#                     mapping.clo_id.write({'plo_ids': [(6, 0, mapping.plo_ids.ids)]})
        
#         return result

#     @api.model
#     def create(self, vals):
#         """Create mapping and update relationships"""
#         mapping = super().create(vals)
        
#         # Update the CLO's plo_ids field
#         if mapping.clo_id and mapping.plo_ids:
#             mapping.clo_id.write({'plo_ids': [(6, 0, mapping.plo_ids.ids)]})
        
#         return mapping

#     def unlink(self):
#         """Update relationships on delete"""
#         for mapping in self:
#             if mapping.clo_id:
#                 # Remove PLO relationships from CLO
#                 mapping.clo_id.write({'plo_ids': [(6, 0, [])]})
#         return super().unlink()

#     def action_activate(self):
#         """Activate the mapping"""
#         self.ensure_one()
#         if not self.plo_ids:
#             raise ValidationError(_('Please map at least one PLO before activating.'))
#         self.state = 'active'
#         self.message_post(body=_('Mapping activated.'))

#     def action_draft(self):
#         """Reset to draft"""
#         self.ensure_one()
#         self.state = 'draft'
#         self.message_post(body=_('Mapping reset to draft.'))

#     def action_archive_mapping(self):
#         """Archive the mapping"""
#         self.ensure_one()
#         self.state = 'archived'
#         self.active = False
#         self.message_post(body=_('Mapping archived.'))


# class ObeCloPloMappingWizard(models.TransientModel):
#     """Wizard for bulk CLO-PLO mapping"""
#     _name = 'obe.clo.plo.mapping.wizard'
#     _description = 'CLO-PLO Mapping Wizard'

#     clo_id = fields.Many2one(
#         'obe.clo',
#         string='Course Learning Outcome',
#         required=True
#     )
    
#     course_id = fields.Many2one(
#         'obe.course',
#         related='clo_id.course_id',
#         string='Course',
#         readonly=True
#     )
    
#     program_id = fields.Many2one(
#         'obe.academic.program',
#         string='Program',
#         help='Filter PLOs by program'
#     )
    
#     plo_ids = fields.Many2many(
#         'obe.plo',
#         string='Program Learning Outcomes',
#         help='Select PLOs to map to this CLO'
#     )
    
#     default_strength = fields.Selection([
#         ('1', 'Low (1)'),
#         ('2', 'Medium (2)'),
#         ('3', 'High (3)'),
#     ], string='Default Strength', default='2', required=True)
    
#     justification = fields.Text(
#         string='Common Justification',
#         help='Common justification for all mappings (can be customized later)'
#     )
    
#     create_single_mapping = fields.Boolean(
#         string='Create Single Mapping Record',
#         default=True,
#         help='If checked, creates one mapping record with all PLOs. Otherwise creates separate records for each PLO.'
#     )
    
#     replace_existing = fields.Boolean(
#         string='Replace Existing Mappings',
#         help='If checked, existing mappings for this CLO will be deleted'
#     )

#     @api.onchange('clo_id')
#     def _onchange_clo_id(self):
#         """Filter PLOs based on course programs"""
#         if self.clo_id and self.clo_id.course_id:
#             program_ids = self.clo_id.course_id.program_ids.ids
#             if program_ids:
#                 self.program_id = program_ids[0]
#             return {
#                 'domain': {
#                     'plo_ids': [('program_id', 'in', program_ids)]
#                 }
#             }

#     @api.onchange('program_id')
#     def _onchange_program_id(self):
#         """Update PLO domain when program changes"""
#         if self.program_id:
#             return {
#                 'domain': {
#                     'plo_ids': [('program_id', '=', self.program_id.id)]
#                 }
#             }

#     def action_create_mappings(self):
#         """Create mappings for selected PLOs"""
#         self.ensure_one()
        
#         if not self.plo_ids:
#             raise ValidationError(_('Please select at least one PLO.'))
        
#         Mapping = self.env['obe.clo.plo.mapping']
#         created_count = 0
        
#         # Delete existing mappings if requested
#         if self.replace_existing:
#             existing = Mapping.search([('clo_id', '=', self.clo_id.id)])
#             if existing:
#                 existing.unlink()
        
#         if self.create_single_mapping:
#             # Create one mapping record with all PLOs
#             Mapping.create({
#                 'clo_id': self.clo_id.id,
#                 'plo_ids': [(6, 0, self.plo_ids.ids)],
#                 'strength': self.default_strength,
#                 'justification': self.justification,
#                 'state': 'active',
#             })
#             created_count = 1
#         else:
#             # Create separate mapping for each PLO
#             for plo in self.plo_ids:
#                 # Check if mapping already exists
#                 existing = Mapping.search([
#                     ('clo_id', '=', self.clo_id.id),
#                     ('plo_ids', 'in', plo.id)
#                 ])
                
#                 if not existing:
#                     Mapping.create({
#                         'clo_id': self.clo_id.id,
#                         'plo_ids': [(6, 0, [plo.id])],
#                         'strength': self.default_strength,
#                         'justification': self.justification,
#                         'state': 'active',
#                     })
#                     created_count += 1
        
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Success'),
#                 'message': _('%s mapping(s) created successfully.') % created_count,
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }


# class ObeCloPloMatrix(models.TransientModel):
#     """Matrix view for CLO-PLO mapping"""
#     _name = 'obe.clo.plo.matrix'
#     _description = 'CLO-PLO Mapping Matrix'

#     course_id = fields.Many2one(
#         'obe.course',
#         string='Course',
#         required=True
#     )
    
#     program_id = fields.Many2one(
#         'obe.academic.program',
#         string='Program',
#         required=True
#     )
    
#     offering_id = fields.Many2one(
#         'obe.course.offering',
#         string='Course Offering',
#         domain="[('course_id', '=', course_id)]"
#     )

#     def action_open_matrix(self):
#         """Open matrix view"""
#         self.ensure_one()
        
#         return {
#             'name': _('CLO-PLO Mapping Matrix'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'obe.clo.plo.mapping',
#             'view_mode': 'pivot,graph,list',
#             'domain': [('course_id', '=', self.course_id.id)],
#             'context': {
#                 'default_course_id': self.course_id.id,
#                 'group_by': ['clo_id', 'plo_ids'],
#             }
#         }


# access_obe_clo_plo_mapping_wizard_admin,obe.clo.plo.mapping.wizard.admin,model_obe_clo_plo_mapping_wizard,group_obe_admin,1,1,1,1
# access_obe_clo_plo_mapping_wizard_coordinator,obe.clo.plo.mapping.wizard.coordinator,model_obe_clo_plo_mapping_wizard,group_obe_coordinator,1,1,1,1
# access_obe_clo_plo_mapping_wizard_faculty,obe.clo.plo.mapping.wizard.faculty,model_obe_clo_plo_mapping_wizard,group_obe_faculty,1,1,1,1
# access_obe_clo_plo_matrix_admin,obe.clo.plo.matrix.admin,model_obe_clo_plo_matrix,group_obe_admin,1,1,1,1
# access_obe_clo_plo_matrix_coordinator,obe.clo.plo.matrix.coordinator,model_obe_clo_plo_matrix,group_obe_coordinator,1,1,1,1
# access_obe_clo_plo_matrix_faculty,obe.clo.plo.matrix.faculty,model_obe_clo_plo_matrix,group_obe_faculty,1,1,1,1