from odoo import models , fields , api 


class OBEAssessmentResult(models.Model):
    """Student-wise assessment results"""
    _name = 'obe.assessment.result'
    _description = 'OBE Assessment Result'
    _order = 'assessment_id, student_id'

    assessment_id = fields.Many2one(
        'obe.assessment',
        string='Assessment',
        
        ondelete='cascade'
    )
    
    student_id = fields.Many2one(
        'obe.student',
        string='Student',
        
        ondelete='cascade'
    )
    
    enrollment_id = fields.Many2one(
        'obe.enrollment',
        string='Enrollment',
        compute='_compute_enrollment',
        store=True
    )
    
 
    total_obtained = fields.Float(
        string='Total Obtained',
        compute='_compute_total_obtained',
        store=True
    )
    
    total_marks = fields.Float(
        related='assessment_id.total_marks',
        string='Total Marks',
        readonly=True
    )
    
    percentage = fields.Float(
        string='Percentage',
        compute='_compute_percentage',
        store=True
    )
    
    # Pass/Fail
    is_passed = fields.Boolean(
        string='Passed',
        compute='_compute_is_passed',
        store=True
    )
    
    # Answers
    answer_ids = fields.One2many(
        'obe.assessment.answer',
        'result_id',
        string='Answers'
    )
    
    # Status
    status = fields.Selection([
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('graded', 'Graded')
    ], string='Status', default='pending')
    
    submission_date = fields.Datetime(string='Submission Date')
    graded_date = fields.Datetime(string='Graded Date')
    graded_by = fields.Many2one('res.users', string='Graded By')
    
    # Remarks
    remarks = fields.Text(string='Remarks')
    
    @api.depends('student_id', 'assessment_id.course_offering_id')
    def _compute_enrollment(self):
        for record in self:
            if record.student_id and record.assessment_id.course_offering_id:
                enrollment = self.env['obe.enrollment'].search([
                    ('student_id', '=', record.student_id.id),
                    ('course_offering_id', '=', record.assessment_id.course_offering_id.id)
                ], limit=1)
                record.enrollment_id = enrollment.id
    
    @api.depends('answer_ids.marks_obtained')
    def _compute_total_obtained(self):
        for record in self:
            record.total_obtained = sum(record.answer_ids.mapped('marks_obtained'))
    
    @api.depends('total_obtained', 'total_marks')
    def _compute_percentage(self):
        for record in self:
            if record.total_marks > 0:
                record.percentage = (record.total_obtained / record.total_marks) * 100
            else:
                record.percentage = 0.0
    
    @api.depends('percentage', 'assessment_id.passing_threshold')
    def _compute_is_passed(self):
        for record in self:
            record.is_passed = record.percentage >= record.assessment_id.passing_threshold
    
  