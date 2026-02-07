# # -*- coding: utf-8 -*-

# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError


# class ObeCourseOffering(models.Model):
#     """Semester-specific Course Offering Management"""
#     _name = 'obe.course.offering'
#     _description = 'Course Offering'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _order = 'academic_year desc, semester desc, section'

#     name = fields.Char(
#         string='Offering Name',
#         compute='_compute_name',
#         store=True
#     )
#     course_id = fields.Many2one(
#         'obe.course',
#         string='Course',
#         required=True,
#         ondelete='cascade',
#         tracking=True
#     )
#     academic_year = fields.Char(
#         string='Academic Year',
#         required=True,
#         tracking=True,
#         help='E.g., 2024-2025'
#     )
#     semester = fields.Selection([
#         ('fall', 'Fall'),
#         ('spring', 'Spring'),
#         ('summer', 'Summer'),
#     ], string='Semester', required=True, tracking=True)
    
#     section = fields.Char(
#         string='Section',
#         required=True,
#         default='A',
#         help='Section identifier (A, B, C, etc.)'
#     )
    
#     instructor_id = fields.Many2one(
#         'res.users',
#         string='Instructor',
#         required=True,
#         domain=[('share', '=', False)],
#         tracking=True,
#         help='Primary instructor for this section'
#     )
    
#     # Additional instructors for team teaching
#     co_instructor_ids = fields.Many2many(
#         'res.users',
#         'offering_co_instructor_rel',
#         'offering_id',
#         'user_id',
#         string='Co-Instructors',
#         domain=[('share', '=', False)]
#     )
    
#     # Schedule
#     start_date = fields.Date(
#         string='Start Date',
#         required=True,
#         tracking=True
#     )
#     end_date = fields.Date(
#         string='End Date',
#         required=True,
#         tracking=True
#     )
    
#     # Enrollment
#     capacity = fields.Integer(
#         string='Capacity',
#         default=40,
#         help='Maximum number of students'
#     )
#     enrolled_count = fields.Integer(
#         string='Enrolled Students',
#         default=0,
#         help='Number of students enrolled'
#     )
    
#     # Location
#     room = fields.Char(
#         string='Room/Location',
#         help='Classroom or lab location'
#     )
#     schedule = fields.Text(
#         string='Class Schedule',
#         help='Days and times (e.g., MW 10:00-11:30)'
#     )
    
#     active = fields.Boolean(
#         string='Active',
#         default=True,
#         tracking=True
#     )
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('scheduled', 'Scheduled'),
#         ('ongoing', 'Ongoing'),
#         ('completed', 'Completed'),
#         ('cancelled', 'Cancelled'),
#     ], string='Status', default='draft', required=True, tracking=True)
    
#     # Relations
#     clo_ids = fields.One2many(
#         'obe.clo',
#         'offering_id',
#         string='Course Learning Outcomes'
#     )
    
#     # Computed fields
#     clo_count = fields.Integer(
#         string='CLO Count',
#         compute='_compute_clo_count',
#         store=True
#     )
    
#     _sql_constraints = [
#         ('unique_offering', 
#          'unique(course_id, academic_year, semester, section)', 
#          'Course offering with same course, year, semester, and section already exists!'),
#         ('positive_capacity', 'check(capacity > 0)', 'Capacity must be positive!'),
#         ('positive_enrolled', 'check(enrolled_count >= 0)', 'Enrolled count cannot be negative!'),
#     ]

#     @api.depends('course_id', 'academic_year', 'semester', 'section')
#     def _compute_name(self):
#         for record in self:
#             if record.course_id:
#                 record.name = f"{record.course_id.code} - {record.academic_year} {record.semester.title()} Sec {record.section}"
#             else:
#                 record.name = 'New Offering'

#     @api.depends('clo_ids')
#     def _compute_clo_count(self):
#         for record in self:
#             record.clo_count = len(record.clo_ids)

#     @api.constrains('start_date', 'end_date')
#     def _check_dates(self):
#         """Validate start and end dates"""
#         for record in self:
#             if record.start_date >= record.end_date:
#                 raise ValidationError(
#                     _('End date must be after start date.')
#                 )

#     @api.constrains('enrolled_count', 'capacity')
#     def _check_enrollment(self):
#         """Validate enrollment doesn't exceed capacity"""
#         for record in self:
#             if record.enrolled_count > record.capacity:
#                 raise ValidationError(
#                     _('Enrolled students cannot exceed capacity.')
#                 )

#     @api.constrains('instructor_id', 'co_instructor_ids')
#     def _check_instructors(self):
#         """Ensure instructors are valid"""
#         for record in self:
#             if record.instructor_id and record.instructor_id.share:
#                 raise ValidationError(
#                     _('Instructor must be an internal user.')
#                 )
#             if record.instructor_id.id in record.co_instructor_ids.ids:
#                 raise ValidationError(
#                     _('Primary instructor cannot also be a co-instructor.')
#                 )

#     @api.model
#     def create(self, vals):
#         """Clone CLOs from master course on creation"""
#         offering = super().create(vals)
#         offering._clone_clos_from_course()
#         return offering

#     def _clone_clos_from_course(self):
#         """Clone CLOs from master course to this offering"""
#         self.ensure_one()
#         # In a full implementation, this would clone template CLOs
#         # For now, we just create a message
#         self.message_post(
#             body=_('Course offering created. CLOs can now be defined for this section.')
#         )

#     def action_schedule(self):
#         """Schedule the offering"""
#         self.ensure_one()
#         if not self.instructor_id:
#             raise ValidationError(_('Please assign an instructor before scheduling.'))
#         self.state = 'scheduled'
#         self.message_post(body=_('Course offering scheduled.'))

#     def action_start(self):
#         """Start the offering"""
#         self.ensure_one()
#         if self.state != 'scheduled':
#             raise ValidationError(_('Only scheduled offerings can be started.'))
#         self.state = 'ongoing'
#         self.message_post(body=_('Course offering started.'))

#     def action_complete(self):
#         """Complete the offering"""
#         self.ensure_one()
#         if self.state != 'ongoing':
#             raise ValidationError(_('Only ongoing offerings can be completed.'))
#         self.state = 'completed'
#         self.message_post(body=_('Course offering completed.'))

#     def action_cancel(self):
#         """Cancel the offering"""
#         self.ensure_one()
#         self.state = 'cancelled'
#         self.active = False
#         self.message_post(body=_('Course offering cancelled.'))

#     def action_view_clos(self):
#         """View CLOs for this offering"""
#         self.ensure_one()
#         return {
#             'name': _('Course Learning Outcomes'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'obe.clo',
#             'view_mode': 'tree,form',
#             'domain': [('offering_id', '=', self.id)],
#             'context': {'default_offering_id': self.id, 'default_course_id': self.course_id.id}
#         }

#     def name_get(self):
#         """Custom name display"""
#         result = []
#         for record in self:
#             name = record.name or 'New Offering'
#             result.append((record.id, name))
#         return result


# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ObeCourseOffering(models.Model):
    _name = 'obe.course.offering'
    _description = 'Course Offering'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'academic_year desc, semester'

    # =============================
    # BASIC INFO
    # =============================
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

    # =============================
    # CAPACITY MANAGEMENT
    # =============================
    max_students = fields.Integer(default=40)
    enrolled_students = fields.Integer(
        compute='_compute_enrollment',
        store=True
    )

    # =============================
    # STATUS
    # =============================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    # =============================
    # RELATIONS
    # =============================
    enrollment_ids = fields.One2many(
        'obe.student.enrollment',
        'offering_id'
    )

    assessment_ids = fields.Many2many(
        'obe.assessment', 
        string="Assessment"
    )

    # =============================
    # COMPUTE METHODS
    # =============================
    @api.depends('course_id', 'academic_year', 'semester', 'section')
    def _compute_name(self):
        for rec in self:
            if rec.course_id:
                rec.name = f"{rec.course_id.code} - {rec.academic_year} {rec.semester} (Sec {rec.section})"

    @api.depends('enrollment_ids')
    def _compute_enrollment(self):
        for rec in self:
            rec.enrolled_students = len(rec.enrollment_ids)

    # =============================
    # CONSTRAINTS
    # =============================
    @api.constrains('max_students')
    def _check_capacity(self):
        for rec in self:
            if rec.max_students <= 0:
                raise ValidationError(_("Capacity must be positive"))

    # =============================
    # STATE ACTIONS
    # =============================
    def action_confirm(self):
        self.state = 'confirmed'

    def action_start(self):
        self.state = 'running'

    def action_complete(self):
        self.state = 'completed'

    def action_cancel(self):
        self.state = 'cancelled'

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
