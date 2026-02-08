# # -*- coding: utf-8 -*-

# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError

# class ObePloPeoMapping(models.Model):
#     """PLO to PEO Mapping with Relationship Strength"""
#     _name = 'obe.plo.peo.mapping'
#     _description = 'PLO-PEO Mapping'
#     _inherit = ['mail.thread']
#     _order = 'plo_id, peo_id'

#     plo_id = fields.Many2one(
#         'obe.plo',
#         string='Program Learning Outcome',
#         required=True,
#         ondelete='cascade',
#         index=True
#     )
#     peo_id = fields.Many2one(
#         'obe.peo',
#         string='Program Educational Objective',
#         required=True,
#         ondelete='cascade',
#         index=True
#     )
#     strength = fields.Selection([
#         ('1', 'Low (1)'),
#         ('2', 'Medium (2)'),
#         ('3', 'High (3)'),
#     ], string='Relationship Strength', required=True, default='2',
#        help='Strength of contribution: 1=Low, 2=Medium, 3=High')
    
#     strength_value = fields.Integer(
#         string='Strength Value',
#         compute='_compute_strength_value',
#         store=True,
#         help='Numeric value for calculations'
#     )
    
#     rationale = fields.Text(
#         string='Supporting Rationale',
#         help='Explanation of how this PLO contributes to the PEO'
#     )
    
#     # Related fields for easier filtering
#     program_id = fields.Many2one(
#         'obe.academic.program',
#         related='plo_id.program_id',
#         string='Program',
#         store=True,
#         readonly=True
#     )
    
#     active = fields.Boolean(
#         string='Active',
#         default=True
#     )
    
#     _sql_constraints = [
#         ('unique_plo_peo', 
#          'unique(plo_id, peo_id)', 
#          'Mapping between this PLO and PEO already exists!'),
#     ]

#     @api.depends('strength')
#     def _compute_strength_value(self):
#         """Convert strength selection to numeric value"""
#         for record in self:
#             record.strength_value = int(record.strength) if record.strength else 0

#     @api.constrains('plo_id', 'peo_id')
#     def _check_same_program(self):
#         """Validate that PLO and PEO belong to the same program"""
#         for record in self:
#             if record.plo_id.program_id != record.peo_id.program_id:
#                 raise ValidationError(
#                     _('PLO and PEO must belong to the same program. '
#                       'PLO is from %s but PEO is from %s.') %
#                     (record.plo_id.program_id.code, record.peo_id.program_id.code)
#                 )

#     def name_get(self):
#         """Custom name display"""
#         result = []
#         for record in self:
#             name = f"{record.plo_id.name} → {record.peo_id.name} (Strength: {record.strength})"
#             result.append((record.id, name))
#         return result

#     @api.model
#     def create(self, vals):
#         """Update many2many on create"""
#         mapping = super().create(vals)
#         # Update the many2many relationships
#         mapping.plo_id.write({'peo_ids': [(4, mapping.peo_id.id)]})
#         mapping.peo_id.write({'plo_ids': [(4, mapping.plo_id.id)]})
#         return mapping

#     def unlink(self):
#         """Update many2many on delete"""
#         for mapping in self:
#             mapping.plo_id.write({'peo_ids': [(3, mapping.peo_id.id)]})
#             mapping.peo_id.write({'plo_ids': [(3, mapping.plo_id.id)]})
#         return super().unlink()


# class ObePloPeoMappingWizard(models.TransientModel):
#     """Wizard for bulk PLO-PEO mapping"""
#     _name = 'obe.plo.peo.mapping.wizard'
#     _description = 'PLO-PEO Mapping Wizard'

#     plo_id = fields.Many2one(
#         'obe.plo',
#         string='Program Learning Outcome',
#         required=True
#     )
#     program_id = fields.Many2one(
#         'obe.academic.program',
#         related='plo_id.program_id',
#         string='Program',
#         readonly=True
#     )
#     peo_ids = fields.Many2many(
#         'obe.peo',
#         string='Program Educational Objectives',
#         help='Select PEOs that this PLO contributes to'
#     )
#     default_strength = fields.Selection([
#         ('1', 'Low (1)'),
#         ('2', 'Medium (2)'),
#         ('3', 'High (3)'),
#     ], string='Default Strength', default='2', required=True)
    
#     rationale = fields.Text(
#         string='Rationale',
#         help='Common rationale for all mappings'
#     )

#     @api.onchange('plo_id')
#     def _onchange_plo_id(self):
#         """Filter PEOs to same program as PLO"""
#         if self.plo_id and self.plo_id.program_id:
#             return {
#                 'domain': {
#                     'peo_ids': [('program_id', '=', self.plo_id.program_id.id)]
#                 }
#             }

#     def action_create_mappings(self):
#         """Create mappings for selected PEOs"""
#         self.ensure_one()
        
#         if not self.peo_ids:
#             raise ValidationError(_('Please select at least one PEO.'))
        
#         Mapping = self.env['obe.plo.peo.mapping']
#         created_count = 0
        
#         for peo in self.peo_ids:
#             # Check if mapping already exists
#             existing = Mapping.search([
#                 ('plo_id', '=', self.plo_id.id),
#                 ('peo_id', '=', peo.id)
#             ])
            
#             if not existing:
#                 Mapping.create({
#                     'plo_id': self.plo_id.id,
#                     'peo_id': peo.id,
#                     'strength': self.default_strength,
#                     'rationale': self.rationale,
#                 })
#                 created_count += 1
        
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

# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ObePloPeoMapping(models.Model):
    """PLO to PEO Mapping with Relationship Strength
    
    Relationship: One PEO has Many Mapping records, each mapping can have Multiple PLOs
    """
    _name = 'obe.plo.peo.mapping'
    _description = 'PLO-PEO Mapping'
    _inherit = ['mail.thread']
    _order = 'peo_id, sequence'
    _rec_name = 'display_name'

    # Basic Information
    peo_id = fields.Many2one(
        'obe.peo',
        string='Program Educational Objective',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    
    plo_ids = fields.Many2many(
        'obe.plo',
        'obe_plo_peo_mapping_plo_rel',
        'mapping_id',
        'plo_id',
        string='Program Learning Outcomes',
        required=True,
        tracking=True,
        help='PLOs that contribute to this PEO'
    )
    
    # Display name for better readability
    display_name = fields.Char(
        string='Mapping',
        compute='_compute_display_name',
        store=True
    )
    
    # Mapping strength
    strength = fields.Selection([
        ('1', 'Low (1)'),
        ('2', 'Medium (2)'),
        ('3', 'High (3)'),
    ], string='Relationship Strength', required=True, default='2',
       help='Strength of contribution: 1=Low, 2=Medium, 3=High',
       tracking=True)
    
    strength_value = fields.Integer(
        string='Strength Value',
        compute='_compute_strength_value',
        store=True,
        help='Numeric value for calculations'
    )
    
    # Justification
    rationale = fields.Text(
        string='Supporting Rationale',
        help='Explanation of how these PLOs contribute to the PEO',
        tracking=True
    )
    
    evidence_reference = fields.Char(
        string='Evidence Reference',
        help='Reference to supporting evidence (curriculum map, assessment data, etc.)'
    )
    
    # Related fields for easier filtering
    program_id = fields.Many2one(
        'obe.academic.program',
        related='peo_id.program_id',
        string='Program',
        store=True,
        readonly=True,
        index=True
    )
    
    institution_id = fields.Many2one(
        'obe.institution',
        related='program_id.institution_id',
        string='Institution',
        store=True,
        readonly=True
    )
    
    # Sequence for ordering
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order within the PEO'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived')
    ], string='Status', default='draft', required=True, tracking=True)
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    
    # Computed field for PLO count
    plo_count = fields.Integer(
        string='PLO Count',
        compute='_compute_plo_count',
        store=True
    )
    
    # Audit fields
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True
    )
    
    last_updated_by = fields.Many2one(
        'res.users',
        string='Last Updated By',
        readonly=True
    )
    
    last_updated_date = fields.Datetime(
        string='Last Updated Date',
        readonly=True
    )

    @api.depends('peo_id', 'plo_ids', 'strength')
    def _compute_display_name(self):
        """Compute display name for the mapping"""
        for record in self:
            if record.peo_id and record.plo_ids:
                plo_names = ', '.join(record.plo_ids.mapped('name'))
                strength_label = dict(record._fields['strength'].selection).get(record.strength, '')
                record.display_name = f"{record.peo_id.name} → [{plo_names}] ({strength_label})"
            else:
                record.display_name = 'New Mapping'

    @api.depends('strength')
    def _compute_strength_value(self):
        """Convert strength selection to numeric value"""
        for record in self:
            record.strength_value = int(record.strength) if record.strength else 0

    @api.depends('plo_ids')
    def _compute_plo_count(self):
        """Count mapped PLOs"""
        for record in self:
            record.plo_count = len(record.plo_ids)

    @api.constrains('plo_ids', 'peo_id')
    def _check_same_program(self):
        """Validate that PLOs and PEO belong to the same program"""
        for record in self:
            if record.plo_ids and record.peo_id:
                for plo in record.plo_ids:
                    if plo.program_id != record.peo_id.program_id:
                        raise ValidationError(
                            _('All PLOs must belong to the same program as the PEO.\n'
                              'PLO "%s" belongs to: %s\n'
                              'PEO belongs to: %s') %
                            (plo.name, plo.program_id.name, record.peo_id.program_id.name)
                        )

    @api.constrains('strength_value')
    def _check_strength_value(self):
        """Validate strength value is within acceptable range"""
        for record in self:
            if record.strength_value < 1 or record.strength_value > 3:
                raise ValidationError(
                    _('Strength value must be between 1 and 3.')
                )

    @api.constrains('plo_ids')
    def _check_plo_ids_not_empty(self):
        """Validate that at least one PLO is selected"""
        for record in self:
            if not record.plo_ids:
                raise ValidationError(
                    _('Please select at least one PLO for this mapping.')
                )

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            if record.peo_id and record.plo_ids:
                plo_names = ', '.join(record.plo_ids.mapped('name')[:3])  # Show first 3
                if len(record.plo_ids) > 3:
                    plo_names += f' (+{len(record.plo_ids) - 3} more)'
                strength_label = dict(record._fields['strength'].selection).get(record.strength, '')
                name = f"{record.peo_id.name} → [{plo_names}] ({strength_label})"
            else:
                name = 'New Mapping'
            result.append((record.id, name))
        return result

    @api.model
    def create(self, vals):
        """Set audit fields on create"""
        vals['created_by'] = self.env.user.id
        vals['created_date'] = fields.Datetime.now()
        mapping = super().create(vals)
        
        # Update the many2many relationships on PEO side
        if mapping.peo_id and mapping.plo_ids:
            mapping.peo_id.write({'plo_ids': [(4, plo.id) for plo in mapping.plo_ids]})
            
            # Update the many2many relationships on PLO side
            for plo in mapping.plo_ids:
                plo.write({'peo_ids': [(4, mapping.peo_id.id)]})
        
        plo_list = ', '.join(mapping.plo_ids.mapped('name'))
        mapping.message_post(
            body=_('Mapping created: %s → [%s] with strength %s') % 
            (mapping.peo_id.name, plo_list, mapping.strength)
        )
        
        return mapping

    def write(self, vals):
        """Update audit fields and maintain relationships on write"""
        vals['last_updated_by'] = self.env.user.id
        vals['last_updated_date'] = fields.Datetime.now()
        
        # Store old PLO IDs before update
        old_plo_ids = {record.id: record.plo_ids.ids for record in self}
        
        result = super().write(vals)
        
        # Update many2many relationships if plo_ids changed
        if 'plo_ids' in vals:
            for record in self:
                old_plos = set(old_plo_ids.get(record.id, []))
                new_plos = set(record.plo_ids.ids)
                
                # PLOs removed from mapping
                removed_plos = old_plos - new_plos
                for plo_id in removed_plos:
                    plo = self.env['obe.plo'].browse(plo_id)
                    plo.write({'peo_ids': [(3, record.peo_id.id)]})
                    record.peo_id.write({'plo_ids': [(3, plo_id)]})
                
                # PLOs added to mapping
                added_plos = new_plos - old_plos
                for plo_id in added_plos:
                    plo = self.env['obe.plo'].browse(plo_id)
                    plo.write({'peo_ids': [(4, record.peo_id.id)]})
                    record.peo_id.write({'plo_ids': [(4, plo_id)]})
        
        return result

    def unlink(self):
        """Update many2many on delete"""
        for mapping in self:
            # Remove from PEO's plo_ids
            if mapping.peo_id and mapping.plo_ids:
                mapping.peo_id.write({'plo_ids': [(3, plo.id) for plo in mapping.plo_ids]})
                
                # Remove from each PLO's peo_ids
                for plo in mapping.plo_ids:
                    plo.write({'peo_ids': [(3, mapping.peo_id.id)]})
            
            plo_list = ', '.join(mapping.plo_ids.mapped('name'))
            mapping.message_post(
                body=_('Mapping deleted: %s → [%s]') % 
                (mapping.peo_id.name, plo_list)
            )
        
        return super().unlink()

    def action_activate(self):
        """Activate the mapping"""
        self.ensure_one()
        if not self.rationale:
            raise ValidationError(
                _('Please provide a rationale before activating this mapping.')
            )
        if not self.plo_ids:
            raise ValidationError(
                _('Please select at least one PLO before activating.')
            )
        self.state = 'active'
        self.message_post(body=_('Mapping activated.'))

    def action_draft(self):
        """Set back to draft"""
        self.ensure_one()
        self.state = 'draft'
        self.message_post(body=_('Mapping set to draft.'))

    def action_archive_mapping(self):
        """Archive the mapping"""
        self.ensure_one()
        self.state = 'archived'
        self.active = False
        self.message_post(body=_('Mapping archived.'))


class ObePloPeoMappingWizard(models.TransientModel):
    """Wizard for bulk PLO-PEO mapping
    
    Allows mapping multiple PLOs to a single PEO at once
    """
    _name = 'obe.plo.peo.mapping.wizard'
    _description = 'PLO-PEO Mapping Wizard'

    peo_id = fields.Many2one(
        'obe.peo',
        string='Program Educational Objective',
        required=True,
        help='Select the PEO to map PLOs to'
    )
    
    program_id = fields.Many2one(
        'obe.academic.program',
        related='peo_id.program_id',
        string='Program',
        readonly=True
    )
    
    plo_ids = fields.Many2many(
        'obe.plo',
        'obe_plo_peo_wizard_plo_rel',
        'wizard_id',
        'plo_id',
        string='Program Learning Outcomes',
        help='Select PLOs to map to this PEO'
    )
    
    default_strength = fields.Selection([
        ('1', 'Low (1)'),
        ('2', 'Medium (2)'),
        ('3', 'High (3)'),
    ], string='Default Strength', default='2', required=True,
       help='Default strength for the mapping')
    
    rationale = fields.Text(
        string='Common Rationale',
        help='Common rationale for the mapping (can be customized later)'
    )
    
    create_single_mapping = fields.Boolean(
        string='Create Single Mapping Record',
        default=True,
        help='If checked, creates one mapping record with all PLOs. If unchecked, creates separate mapping for each PLO.'
    )
    
    replace_existing = fields.Boolean(
        string='Replace Existing Mappings',
        default=False,
        help='If checked, existing mappings will be deleted before creating new ones'
    )

    @api.onchange('peo_id')
    def _onchange_peo_id(self):
        """Filter PLOs to same program as PEO"""
        if self.peo_id and self.peo_id.program_id:
            return {
                'domain': {
                    'plo_ids': [('program_id', '=', self.peo_id.program_id.id)]
                }
            }
        return {'domain': {'plo_ids': []}}

    def action_create_mappings(self):
        """Create mappings for selected PLOs"""
        self.ensure_one()
        
        if not self.plo_ids:
            raise ValidationError(_('Please select at least one PLO.'))
        
        Mapping = self.env['obe.plo.peo.mapping']
        
        # Delete existing mappings if replace_existing is True
        if self.replace_existing:
            existing = Mapping.search([
                ('peo_id', '=', self.peo_id.id),
                ('plo_ids', 'in', self.plo_ids.ids)
            ])
            if existing:
                existing.unlink()
        
        if self.create_single_mapping:
            # Create ONE mapping record with all selected PLOs
            Mapping.create({
                'peo_id': self.peo_id.id,
                'plo_ids': [(6, 0, self.plo_ids.ids)],
                'strength': self.default_strength,
                'rationale': self.rationale,
                'state': 'draft',
            })
            message = _('1 mapping created with %s PLO(s).') % len(self.plo_ids)
        else:
            # Create SEPARATE mapping record for each PLO
            created_count = 0
            skipped_count = 0
            
            for plo in self.plo_ids:
                # Check if mapping already exists
                existing = Mapping.search([
                    ('peo_id', '=', self.peo_id.id),
                    ('plo_ids', 'in', [plo.id])
                ])
                
                if not existing:
                    Mapping.create({
                        'peo_id': self.peo_id.id,
                        'plo_ids': [(6, 0, [plo.id])],
                        'strength': self.default_strength,
                        'rationale': self.rationale,
                        'state': 'draft',
                    })
                    created_count += 1
                else:
                    skipped_count += 1
            
            message = _('%s mapping(s) created successfully.') % created_count
            if skipped_count > 0:
                message += _('\n%s mapping(s) already existed and were skipped.') % skipped_count
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }