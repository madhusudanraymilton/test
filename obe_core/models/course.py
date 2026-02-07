# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ObeCourse(models.Model):

    _name = 'obe.course'
    _description = 'Course'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code'

    name = fields.Char(
        string='Course Title',
        required=True,
        tracking=True,
        help='Full course title'
    )
    code = fields.Char(
        string='Course Code',
        required=True,
        tracking=True,
        help='Unique course code (6-10 alphanumeric characters)'
    )
    credit_hours = fields.Float(
        string='Credit Hours',
        required=True,
        default=3.0,
        help='Total credit hours (1-6)'
    )
    theory_hours = fields.Float(
        string='Theory Hours',
        default=3.0,
        help='Theory lecture hours per week'
    )
    lab_hours = fields.Float(
        string='Lab Hours',
        default=0.0,
        help='Laboratory hours per week'
    )
    state = fields.Selection([('draft','Draft'),('confirm','Confirm')],string="Status", default='draft', tracking=True)
    semester = fields.Selection([
        ('1', '1st Semester'),
        ('2', '2nd Semester'),
        ('3', '3rd Semester'),
        ('4', '4th Semester'),
        ('5', '5th Semester'),
        ('6', '6th Semester'),
        ('7', '7th Semester'),
        ('8', '8th Semester')
    ], string='Recommended Semester', help='Recommended semester for this course')
    
    course_type = fields.Selection([
        ('theory', 'Theory'),
        ('lab', 'Laboratory'),
        ('project', 'Project'),
        ('thesis', 'Thesis'),
    ], string='Course Type', required=True, default='theory', tracking=True)

    program_ids = fields.Many2many(
        'obe.academic.program',
        'program_course_rel',
        'course_id',
        'program_id',
        string='Programs',
        help='Programs offering this course'
    )
    coordinator_id = fields.Many2one(
        'res.users',
        string='Course Coordinator',
        domain=[('share', '=', False)],
        tracking=True,
        help='Faculty responsible for course coordination'
    )
    
    # Prerequisites
    prerequisite_ids = fields.Many2many(
        'obe.course',
        'course_prerequisite_rel',
        'course_id',
        'prerequisite_id',
        string='Prerequisites',
        help='Courses required before taking this course'
    )
    dependent_course_ids = fields.Many2many(
        'obe.course',
        'course_prerequisite_rel',
        'prerequisite_id',
        'course_id',
        string='Dependent Courses',
        help='Courses that require this course as prerequisite'
    )

    # Course Content
    syllabus = fields.Html(
        string='Syllabus',
        help='Detailed course syllabus'
    )
    description = fields.Text(
        string='Course Description',
        help='Brief course description'
    )
    learning_objectives = fields.Text(
        string='Learning Objectives',
        help='High-level learning objectives'
    )

    syllabus_note = fields.Html(
        string="Syllabus Note",
        sanitize=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    
    offering_ids = fields.One2many(
        'obe.course.offering',
        'course_id',
        string='Course Offerings'
    )
    offering_count = fields.Integer(
        string='Offering Count',
        compute='_compute_offering_count',
        store=True
    )
    program_count = fields.Integer(
        string='Program Count',
        compute='_compute_program_count',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
    ], string='Status', default='draft', required=True, tracking=True)
    
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

    @api.depends('offering_ids')
    def _compute_offering_count(self):
        for record in self:
            record.offering_count = len(record.offering_ids)

    @api.depends('program_ids')
    def _compute_program_count(self):
        for record in self:
            record.program_count = len(record.program_ids)

   

    @api.constrains('prerequisite_ids')
    def _check_circular_prerequisites(self):
        """Prevent circular prerequisite dependencies"""
        for record in self:
            if record in record.prerequisite_ids:
                raise ValidationError(
                    _('A course cannot be its own prerequisite.')
                )
            # Check for circular dependencies
            visited = set()
            stack = list(record.prerequisite_ids)
            while stack:
                prereq = stack.pop()
                if prereq.id == record.id:
                    raise ValidationError(
                        _('Circular prerequisite dependency detected.')
                    )
                if prereq.id not in visited:
                    visited.add(prereq.id)
                    stack.extend(prereq.prerequisite_ids)

    @api.constrains('coordinator_id')
    def _check_coordinator_role(self):
        """Ensure coordinator has appropriate role"""
        for record in self:
            if record.coordinator_id and record.coordinator_id.share:
                raise ValidationError(
                    _('Course coordinator must be an internal user.')
                )

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Enhanced search to include course code"""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)] + domain
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

    def action_view_offerings(self):
        """View course offerings"""
        self.ensure_one()
        return {
            'name': _('Course Offerings'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.course.offering',
            'view_mode': 'list,form',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id}
        }

    def action_view_prerequisites(self):
        """View prerequisite tree"""
        self.ensure_one()
        return {
            'name': _('Prerequisites'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.course',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.prerequisite_ids.ids)],
        }

    def get_prerequisite_tree(self):
        """Recursively get all prerequisites"""
        self.ensure_one()
        all_prerequisites = set()
        
        def _get_prereqs(course):
            for prereq in course.prerequisite_ids:
                if prereq.id not in all_prerequisites:
                    all_prerequisites.add(prereq.id)
                    _get_prereqs(prereq)
        
        _get_prereqs(self)
        return self.browse(list(all_prerequisites))