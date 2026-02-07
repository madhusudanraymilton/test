# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ObePLO(models.Model):
    """Program Learning Outcomes Management"""
    _name = 'obe.plo'
    _description = 'Program Learning Outcome (PLO/PO)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'program_id, sequence, name'

    name = fields.Char(
        string='PLO Code',
        required=True,
        tracking=True,
        help='E.g., PO1, PO2, PLO1'
    )
    created_date = fields.Date(
        string="Created Date",
        default=fields.Date.context_today 
    )
    description = fields.Text(
        string='Outcome Description',
        required=True,
        tracking=True,
        help='What students should know/be able to do upon program completion'
    )
    program_id = fields.Many2one(
        'obe.academic.program',
        string='Program',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    code = fields.Char(string='Institution Code', required=True, tracking=True)
    bloom_level = fields.Selection([
        ('remember', 'Remember'),
        ('understand', 'Understand'),
        ('apply', 'Apply'),
        ('analyze', 'Analyze'),
        ('evaluate', 'Evaluate'),
        ('create', 'Create'),

    ], string='Bloom\'s Taxonomy Level', required=True, tracking=True)
    
    cognitive_level = fields.Selection([
        ('knowledge', 'Knowledge'),
        ('comprehension', 'Comprehension'),
        ('application', 'Application'),
        ('analysis', 'Analysis'),
        ('synthesis', 'Synthesis'),
        ('evaluation', 'Evaluation'),
    ], string='Cognitive Level', help='Alternative cognitive level classification')
    
    # Accreditation Mapping
    accreditation_mapping = fields.Selection([
        # ABET Criteria (a-k)
        ('abet_a', 'ABET (a): Engineering knowledge'),
        ('abet_b', 'ABET (b): Problem analysis'),
        ('abet_c', 'ABET (c): Design/development of solutions'),
        ('abet_d', 'ABET (d): Investigation'),
        ('abet_e', 'ABET (e): Modern tool usage'),
        ('abet_f', 'ABET (f): Professional and ethical responsibility'),
        ('abet_g', 'ABET (g): Communication'),
        ('abet_h', 'ABET (h): Impact of engineering solutions'),
        ('abet_i', 'ABET (i): Lifelong learning'),
        ('abet_j', 'ABET (j): Contemporary issues'),
        ('abet_k', 'ABET (k): Use of techniques/tools'),
        # BAETE Graduate Attributes
        ('baete_ga1', 'BAETE GA1: Engineering knowledge'),
        ('baete_ga2', 'BAETE GA2: Problem analysis'),
        ('baete_ga3', 'BAETE GA3: Design/development of solutions'),
        ('baete_ga4', 'BAETE GA4: Investigation'),
        ('baete_ga5', 'BAETE GA5: Modern tool usage'),
        ('baete_ga6', 'BAETE GA6: Engineer and society'),
        ('baete_ga7', 'BAETE GA7: Environment and sustainability'),
        ('baete_ga8', 'BAETE GA8: Ethics'),
        ('baete_ga9', 'BAETE GA9: Individual and teamwork'),
        ('baete_ga10', 'BAETE GA10: Communication'),
        ('baete_ga11', 'BAETE GA11: Project management'),
        ('baete_ga12', 'BAETE GA12: Lifelong learning'),
        # NBA Program Outcomes
        ('nba_po1', 'NBA PO1: Engineering knowledge'),
        ('nba_po2', 'NBA PO2: Problem analysis'),
        ('nba_po3', 'NBA PO3: Design/development of solutions'),
        ('nba_po4', 'NBA PO4: Conduct investigations'),
        ('nba_po5', 'NBA PO5: Modern tool usage'),
        ('nba_po6', 'NBA PO6: Engineer and society'),
        ('nba_po7', 'NBA PO7: Environment and sustainability'),
        ('nba_po8', 'NBA PO8: Ethics'),
        ('nba_po9', 'NBA PO9: Individual and teamwork'),
        ('nba_po10', 'NBA PO10: Communication'),
        ('nba_po11', 'NBA PO11: Project management and finance'),
        ('nba_po12', 'NBA PO12: Lifelong learning'),
    ], string='Accreditation Standard Mapping', tracking=True)
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    target_attainment = fields.Float(
        string='Target Attainment %',
        default=70.0,
        help='Expected percentage of students achieving this PLO'
    )

    peo_ids = fields.Many2many(
        'obe.peo',
        'plo_peo_rel',
        'plo_id',
        'peo_id',
        string='Related PEOs',
        help='PEOs to which this PLO contributes'
    )
    clo_ids = fields.Many2many(
        'obe.clo',
        'clo_plo_rel',
        'plo_id',
        'clo_id',
        string='Mapped CLOs',
        help='Course Learning Outcomes mapped to this PLO'
    )

    peo_count = fields.Integer(
        string='Related PEO Count',
        compute='_compute_counts',
        store=True
    )
    clo_count = fields.Integer(
        string='Mapped CLO Count',
        compute='_compute_counts',
        store=True
    )
    institution_id = fields.Many2one('obe.institution', string='Institution', required=True, ondelete='cascade')
    website = fields.Char(string="Website")
    
    @api.onchange('institution_id')
    def get_institution(self):
        self.code = self.institution_id.code 
        self.website = self.institution_id.website


    @api.depends('peo_ids', 'clo_ids')
    def _compute_counts(self):
        for record in self:
            record.peo_count = len(record.peo_ids)
            record.clo_count = len(record.clo_ids)

  

    @api.constrains('peo_ids')
    def _check_peo_mapping(self):
        """Ensure each PLO maps to at least one PEO"""
        for record in self:
            if record.state in ['approved', 'published'] and not record.peo_ids:
                raise ValidationError(
                    _('PLO must be mapped to at least one PEO before approval.')
                )

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.program_id.code} - {record.name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Enhanced search to include program code"""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('program_id.code', operator, name)] + domain
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    def action_submit_for_review(self):
        """Submit PLO for review"""
        self.ensure_one()
        if not self.peo_ids:
            raise ValidationError(_('Please map this PLO to at least one PEO before submitting.'))
        self.state = 'review'
        self.message_post(body=_('PLO submitted for review.'))
        
        if self.program_id.coordinator_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.program_id.coordinator_id.id,
                summary=_('PLO action_activeReview Required'),
                note=_('Please review PLO: %s') % self.name
            )

    def action_approve(self):
        """Approve the PLO"""
        self.ensure_one()
        if self.state != 'review':
            raise ValidationError(_('Only PLOs under review can be approved.'))
        if not self.peo_ids:
            raise ValidationError(_('PLO must be mapped to at least one PEO.'))
        self.state = 'approved'
        self.message_post(body=_('PLO approved.'))

    def action_publish(self):
        """Publish the PLO"""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_('Only approved PLOs can be published.'))
        self.state = 'published'
        self.message_post(body=_('PLO published.'))

  
    def action_view_peos(self):
        """View related PEOs"""
        self.ensure_one()
        return {
            'name': _('Related PEOs'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.peo',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.peo_ids.ids)],
        }

    def action_view_clos(self):
        """View mapped CLOs"""
        self.ensure_one()
        return {
            'name': _('Mapped CLOs'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.clo',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.clo_ids.ids)],
        }
    
    def action_active(self):
        """Confirm and activate the record"""
        self.ensure_one()
        self.write({'state': 'active'})
        return True

    def action_draft(self):
        """Reset to draft state"""
        self.ensure_one()
        self.write({'state': 'draft'})
        return True