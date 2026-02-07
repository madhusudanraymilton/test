# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ObeAcademicProgram(models.Model):
    """Academic Program Management"""
    _name = 'obe.academic.program'
    _description = 'Academic Program'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    

    ref_name = fields.Char(string="Reference", default="New", readonly=True, copy=False)
    name = fields.Char(
        string='Program Name',
       
        tracking=True,
        help='Full name of the academic program'
    )
    code = fields.Char(
        string='Program Code',
       
        tracking=True,
        help='Unique program code (4-12 alphanumeric characters)'
    )
    institution_id = fields.Many2one(
        'obe.institution',
        string='Institution',
       
        ondelete='restrict',
        tracking=True 
    )
    institution_code = fields.Char(string='Institution Code', tracking=True)
    degree_level = fields.Selection([
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('phd', 'PhD'),
    ], string='Degree Level',required=True, tracking=True)
    
    duration_years = fields.Float(
        string='Duration (Years)',
        default=4.0,
        help='Total duration of the program in years'
    )
    total_credits = fields.Float(
        string='Total Credits',
        help='Total credit hours required for graduation'
    )
    accreditation_body = fields.Selection([
        ('baete', 'BAETE'),
        ('abet', 'ABET'),
        ('nba', 'NBA'),
        ('washington', 'Washington Accord'),
        ('other', 'Other')
    ], string='Accreditation Body',tracking=True)
    
    start_date = fields.Date(
        string='Start Date',
        tracking=True,
        help='Program commencement date'
    )
    end_date = fields.Date(
        string='End Date',
        tracking=True,
        help='Program discontinuation date (if applicable)'
    )
    
    coordinator_id = fields.Many2one(
        'res.users',
        string='Program Coordinator',
        tracking=True,
        domain=[('share', '=', False)],
        help='Faculty member responsible for program coordination'
    )
    
    description = fields.Text(
        string='Program Description',
        help='Detailed description of the program'
    )

    objectives = fields.Text(
        string='Program Objectives',
        help='High-level program objectives'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed')
    ], string='Status', default='draft', tracking=True)
    
    # Relations
    peo_ids = fields.One2many(
        'obe.peo',
        'program_id',
        string='Program Educational Objectives (PEOs)'
    )
    plo_ids = fields.One2many(
        'obe.plo',
        'program_id',
        string='Program Learning Outcomes (PLOs)'
    )
    course_ids = fields.Many2many(
        'obe.course',
        'program_course_rel',
        'program_id',
        'course_id',
        string='Courses'
    )
    
    # Computed fields
    peo_count = fields.Integer(
        string='PEO Count',
        compute='_compute_counts',
        store=True
    )
    plo_count = fields.Integer(
        string='PLO Count',
        compute='_compute_counts',
        store=True
    )
    course_count = fields.Integer(
        string='Course Count',
        compute='_compute_counts',
        store=True
    )
    
    # Version control
    version = fields.Integer(
        string='Version',
        default=1,
        readonly=True
    )

    @api.onchange("institution_id")
    def get_institution(self):
        self.institution_code = self.institution_id.code 
    

    @api.depends('peo_ids', 'plo_ids', 'course_ids')
    def _compute_counts(self):
        for record in self:
            record.peo_count = len(record.peo_ids)
            record.plo_count = len(record.plo_ids)
            record.course_count = len(record.course_ids)

    @api.constrains('code')
    def _check_code_format(self):
        """Validate program code format: 4-12 alphanumeric characters"""
        for record in self:
            if not re.match(r'^[A-Za-z0-9]{4,12}$', record.code):
                raise ValidationError(
                    _('Program code must be 4-12 alphanumeric characters only.')
                )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """Validate start and end dates"""
        for record in self:
            if record.end_date and record.start_date >= record.end_date:
                raise ValidationError(
                    _('End date must be after start date.')
                )

    @api.constrains('coordinator_id')
    def _check_coordinator_role(self):
        for record in self:
            if record.coordinator_id and record.coordinator_id.share:
                raise ValidationError(
                    _('Coordinator must be an internal user (faculty/staff).')
                )

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result

    def action_approve(self):
        """Approve the program"""
        self.ensure_one()
        if not self.coordinator_id:
            raise ValidationError(_('Please assign a program coordinator before approval.'))
        self.state = 'approved'
        self.message_post(body=_('Program approved.'))

    def action_activate(self):
        """Activate the program"""
        self.ensure_one()
        self.state = 'active'
        self.message_post(body=_('Program activated.'))


    def action_suspend(self):
        """Suspend the program"""
        self.ensure_one()
        self.state = 'suspended'
        self.message_post(body=_('Program suspended.'))

    def action_close(self):
        """Close the program"""
        self.ensure_one()
        self.state = 'closed'
        self.active = False
        self.message_post(body=_('Program closed.'))

    def action_draft(self):
        """Set back to draft"""
        self.ensure_one()
        self.state = 'draft'

    def action_view_peos(self):
        """View PEOs for this program"""
        self.ensure_one()
        return {
            'name': _('Program Educational Objectives'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.peo',
            'view_mode': 'tree,form',
            'domain': [('program_id', '=', self.id)],
            'context': {'default_program_id': self.id}
        }

    def action_view_plos(self):
        """View PLOs for this program"""
        self.ensure_one()
        return {
            'name': _('Program Learning Outcomes'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.plo',
            'view_mode': 'tree,form',
            'domain': [('program_id', '=', self.id)],
            'context': {'default_program_id': self.id}
        }

    def action_view_courses(self):
        """View courses for this program"""
        self.ensure_one()
        return {
            'name': _('Program Courses'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.course',
            'view_mode': 'tree,form',
            'domain': [('program_ids', 'in', self.id)],
            'context': {'default_program_ids': [(6, 0, [self.id])]}
        }
    


    @api.model
    def create(self, vals):

        if vals.get('ref_name', 'New') == 'New':
            last_record = self.search(
                [('ref_name', 'like', 'PEO/%')],
                order='id desc',
                limit=1
            )
            
            if last_record and last_record.ref_name:
                try:
                    last_seq = int(last_record.ref_name.split('/')[-1])
                    next_seq = str(last_seq + 1).zfill(5)
                except:
                    next_seq = '00001'
            else:
                next_seq = '00001'

            vals['ref_name'] = f"PEO/{next_seq}"

        return super(ObeAcademicProgram, self).create(vals)

    def initialize_plo_template(self):
        """Initialize PLO template based on accreditation body"""
        self.ensure_one()
        
        templates = {
            'abet': [
                ('PO1', 'An ability to identify, formulate, and solve complex engineering problems'),
                ('PO2', 'An ability to apply engineering design'),
                ('PO3', 'An ability to communicate effectively'),
                ('PO4', 'An ability to recognize ethical and professional responsibilities'),
                ('PO5', 'An ability to function effectively on a team'),
            ],
            'baete': [
                ('GA1', 'Engineering Knowledge'),
                ('GA2', 'Problem Analysis'),
                ('GA3', 'Design/Development of Solutions'),
                ('GA4', 'Investigation'),
                ('GA5', 'Modern Tool Usage'),
            ],
            'nba': [
                ('PO1', 'Engineering knowledge'),
                ('PO2', 'Problem analysis'),
                ('PO3', 'Design/development of solutions'),
                ('PO4', 'Conduct investigations of complex problems'),
                ('PO5', 'Modern tool usage'),
            ]
        }
        
        template = templates.get(self.accreditation_body, [])
        PLO = self.env['obe.plo']
        
        for code, description in template:
            PLO.create({
                'name': code,
                'description': description,
                'program_id': self.id,
                'state': 'draft',
            })
        
        self.message_post(body=_('PLO template initialized with %s outcomes.') % len(template))