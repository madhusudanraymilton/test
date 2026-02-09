

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ObeCourseOffering(models.Model):
    _name = 'obe.course.offering'
    _description = 'Course Offering'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'academic_year desc, semester'

 
    name = fields.Char(
        string='Offering Name',
        compute='_compute_name',
        store=True
    )

    course_id = fields.Many2one(
        'obe.course',
        required=True,
        tracking=True
    )

    academic_year = fields.Char(
        required=True,
        tracking=True,
        help="Example: 2025-2026"
    )

    semester = fields.Selection([
        ('first', "1st Semester"),
        ("second", "2nd Semester"),
        ("third", "3rd Semester"),
        ("fourth", "4th Semester"),
        ("fifth", "5th Semester"),
        ("sixth", "6th Semester"),
        ("seventh", "7th Semester"),
        ("eighth", "8th Semester")
    ], required=True, tracking=True)

    section = fields.Char(
        string="Section",
        default="A",
        tracking=True
    )

    instructor_id = fields.Many2many(
        'hr.employee',
        domain=[('share', '=', False)],
        tracking=True
    )

  
    max_students = fields.Integer(default=40)
    enrolled_students = fields.Integer(
        compute='_compute_enrollment',
        store=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft', tracking=True)

    enrollment_ids = fields.One2many(
        'obe.student.enrollment',
        'offering_id'
    )

    assessment_ids = fields.Many2many(
        'obe.assessment', 
        string="Assessment"
    )

    def action_draft(self):
        self.state = 'draft'
    def action_confirmed(self):
        self.state = 'confirmed'

    @api.depends('course_id', 'academic_year', 'semester', 'section')
    def _compute_name(self):
        for rec in self:
            if rec.course_id:
                rec.name = f"{rec.course_id.code} - {rec.academic_year} {rec.semester} (Sec {rec.section})"

    @api.depends('enrollment_ids')
    def _compute_enrollment(self):
        for rec in self:
            rec.enrolled_students = len(rec.enrollment_ids)

 
    @api.constrains('max_students')
    def _check_capacity(self):
        for rec in self:
            if rec.max_students <= 0:
                raise ValidationError(_("Capacity must be positive"))


class ObeStudentEnrollment(models.Model):
    _name = 'obe.student.enrollment'
    _description = 'Student Enrollment'

    student_id = fields.Many2one('res.partner', required=True)
    offering_id = fields.Many2one('obe.course.offering')

    registration_date = fields.Date(default=fields.Date.today)

    status = fields.Selection([
        ('enrolled', 'Enrolled'),
        ('dropped', 'Dropped'),
        ('completed', 'Completed')
    ], default='enrolled')
