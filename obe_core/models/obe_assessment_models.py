# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class OBEAssessment(models.Model):
    
    _name = 'obe.assessment'
    _description = 'OBE Assessment'
    _order = 'assessment_date desc, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(
        string='Assessment Name',
        
        tracking=True,
        help='Name of the assessment (e.g., Midterm Exam, Quiz 1)'
    )
    
    assessment_type = fields.Selection([
        ('exam', 'Exam'),
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('project', 'Project'),
        ('lab', 'Lab'),
        ('presentation', 'Presentation'),
        ('viva', 'Viva'),
        ('other', 'Other')
    ], string='Assessment Type',  tracking=True)
    
    course_offering_id = fields.Many2one(
        'obe.course.offering',
        string='Course Offering',
        
        ondelete='cascade',
        tracking=True
    )
    
    course_id = fields.Many2one(
        'obe.course',
        string='Course',
        related='course_offering_id.course_id',
        store=True,
        readonly=True
    )
    
    # semester_id = fields.Many2one(
    #     'obe.semester',
    #     string='Semester',
    #     related='course_offering_id.semester_id',
    #     store=True,
    #     readonly=True
    # )
    
    # Marks and Weightage
    total_marks = fields.Float(
        string='Total Marks',
        
        tracking=True,
        help='Maximum marks for this assessment'
    )
    
    weightage = fields.Float(
        string='Weightage (%)',
        
        tracking=True,
        help='Contribution percentage towards final grade'
    )
    
    passing_threshold = fields.Float(
        string='Passing Threshold (%)',
        default=60.0,
        
        help='Minimum percentage required to pass this assessment'
    )
    
    # Date and Status
    assessment_date = fields.Date(
        string='Assessment Date',
        
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('graded', 'Graded'),
        ('finalized', 'Finalized')
    ], string='Status', default='draft', tracking=True)
    
    # CLO Mapping
    clo_ids = fields.Many2many(
        'obe.clo',
        'obe_assessment_clo_rel',
        'assessment_id',
        'clo_id',
        string='Mapped CLOs',
        help='Course Learning Outcomes covered by this assessment'
    )
    
    clo_count = fields.Integer(
        string='CLO Count',
        compute='_compute_clo_count',
        store=True
    )
    
    # Questions
    question_ids = fields.One2many(
        'obe.assessment.question',
        'assessment_id',
        string='Questions'
    )
    
    question_count = fields.Integer(
        string='Question Count',
        compute='_compute_question_count',
        store=True
    )
    
    # Student Results
    result_ids = fields.One2many(
        'obe.assessment.result',
        'assessment_id',
        string='Student Results'
    )
    
    result_count = fields.Integer(
        string='Results Count',
        compute='_compute_result_count',
        store=True
    )
    
    # Computed Fields
    total_question_marks = fields.Float(
        string='Total Question Marks',
        compute='_compute_total_question_marks',
        store=True,
        help='Sum of all question marks'
    )
    
    average_marks = fields.Float(
        string='Average Marks',
        compute='_compute_statistics',
        store=True
    )
    
    pass_percentage = fields.Float(
        string='Pass Percentage',
        compute='_compute_statistics',
        store=True
    )
    
    # Additional Information
    description = fields.Text(string='Description')
    instructions = fields.Html(string='Instructions')
    duration_minutes = fields.Integer(string='Duration (Minutes)')
    
    faculty_id = fields.Many2one(
        'res.users',
        string='Faculty',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    active = fields.Boolean(default=True)
    
    @api.depends('clo_ids')
    def _compute_clo_count(self):
        for record in self:
            record.clo_count = len(record.clo_ids)
    
    @api.depends('question_ids')
    def _compute_question_count(self):
        for record in self:
            record.question_count = len(record.question_ids)
    
    @api.depends('result_ids')
    def _compute_result_count(self):
        for record in self:
            record.result_count = len(record.result_ids)
    
    @api.depends('question_ids.marks')
    def _compute_total_question_marks(self):
        for record in self:
            record.total_question_marks = sum(record.question_ids.mapped('marks'))
    
    @api.depends('result_ids.total_obtained', 'result_ids.is_passed')
    def _compute_statistics(self):
        for record in self:
            if record.result_ids:
                record.average_marks = sum(record.result_ids.mapped('total_obtained')) / len(record.result_ids)
                passed_count = len(record.result_ids.filtered('is_passed'))
                record.pass_percentage = (passed_count / len(record.result_ids)) * 100
            else:
                record.average_marks = 0.0
                record.pass_percentage = 0.0
    
    @api.constrains('total_marks')
    def _check_total_marks(self):
        for record in self:
            if record.total_marks <= 0:
                raise ValidationError(_('Total marks must be positive.'))
    
    @api.constrains('weightage')
    def _check_weightage(self):
        for record in self:
            if record.weightage <= 0 or record.weightage > 100:
                raise ValidationError(_('Weightage must be between 0 and 100.'))
    
    @api.constrains('passing_threshold')
    def _check_passing_threshold(self):
        for record in self:
            if record.passing_threshold < 0 or record.passing_threshold > 100:
                raise ValidationError(_('Passing threshold must be between 0 and 100.'))
    
    @api.constrains('clo_ids')
    def _check_clo_mapping(self):
        for record in self:
            if not record.clo_ids:
                raise ValidationError(_('Assessment must be mapped to at least one CLO.'))
    

    @api.constrains('course_offering_id')
    def _check_total_weightage(self):
        """Validate that total weightage of all assessments = 100%"""
        for record in self:
            if record.course_offering_id:
                total_weightage = sum(
                    record.course_offering_id.assessment_ids.filtered(
                        lambda a: a.state != 'draft'
                    ).mapped('weightage')
                )
                if total_weightage > 100:
                    raise ValidationError(
                        _('Total weightage for course offering exceeds 100%. Current total: %.2f%%') % total_weightage
                    )
    
    def action_schedule(self):
        self.write({'state': 'scheduled'})
    
    def action_start(self):
        self.write({'state': 'in_progress'})
    
    def action_complete(self):
        self.write({'state': 'completed'})
    
    def action_grade(self):
        self.write({'state': 'graded'})
    
    def action_finalize(self):
        # Validate before finalizing
        for record in self:
            if abs(record.total_marks - record.total_question_marks) > 0.01:
                raise ValidationError(
                    _('Total question marks (%.2f) does not match assessment total marks (%.2f)') % 
                    (record.total_question_marks, record.total_marks)
                )
        self.write({'state': 'finalized'})
        self._calculate_clo_attainment()
    
    def _calculate_clo_attainment(self):
        """Calculate CLO attainment after assessment finalization"""
        for record in self:
            AttainmentObj = self.env['obe.clo.attainment']
            for clo in record.clo_ids:
                AttainmentObj.calculate_clo_attainment(
                    clo_id=clo.id,
                    offering_id=record.course_offering_id.id,
                    assessment_id=record.id
                )
    
    def action_view_questions(self):
        return {
            'name': _('Assessment Questions'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.assessment.question',
            'view_mode': 'tree,form',
            'domain': [('assessment_id', '=', self.id)],
            'context': {'default_assessment_id': self.id}
        }
    
    def action_view_results(self):
        return {
            'name': _('Assessment Results'),
            'type': 'ir.actions.act_window',
            'res_model': 'obe.assessment.result',
            'view_mode': 'tree,form',
            'domain': [('assessment_id', '=', self.id)],
            'context': {'default_assessment_id': self.id}
        }


class OBEAssessmentQuestion(models.Model):
    """
    FR-011: Question-Level CLO Mapping
    Supports granular question-level CLO mapping for comprehensive attainment tracking
    """
    _name = 'obe.assessment.question'
    _description = 'OBE Assessment Question'
    _order = 'assessment_id, sequence, question_number'

    # Basic Information
    name = fields.Char(
        string='Question Reference',
        compute='_compute_name',
        store=True
    )
    
    assessment_id = fields.Many2one(
        'obe.assessment',
        string='Assessment',
        
        ondelete='cascade'
    )
    
    sequence = fields.Integer(string='Sequence', default=10)
    
    question_number = fields.Char(
        string='Question Number',
        
        help='Question identifier (e.g., Q1, 1a, 2.1)'
    )
    
    question_text = fields.Text(
        string='Question Text',
        required=True
    )
    
    # Marks
    marks = fields.Float(
        string='Marks',
        
        help='Maximum marks for this question'
    )
    
    # CLO Mapping
    clo_id = fields.Many2one(
        'obe.clo',
        string='Mapped CLO',
        
        help='Course Learning Outcome assessed by this question'
    )
    
    # Bloom's Taxonomy
    bloom_level = fields.Selection([
        ('remember', 'Remember (L1)'),
        ('understand', 'Understand (L2)'),
        ('apply', 'Apply (L3)'),
        ('analyze', 'Analyze (L4)'),
        ('evaluate', 'Evaluate (L5)'),
        ('create', 'Create (L6)')
    ], string='Bloom Level', required=True)
    
    # Question Details
    question_type = fields.Selection([
        ('mcq', 'Multiple Choice'),
        ('short_answer', 'Short Answer'),
        ('long_answer', 'Long Answer'),
        ('numerical', 'Numerical'),
        ('true_false', 'True/False'),
        ('practical', 'Practical'),
        ('code', 'Programming/Code')
    ], string='Question Type', default='short_answer')
    
    difficulty_level = fields.Selection([
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ], string='Difficulty Level', default='medium')
    
    # Student Answers
    answer_ids = fields.One2many(
        'obe.assessment.answer',
        'question_id',
        string='Student Answers'
    )
    
    # Statistics
    average_marks_obtained = fields.Float(
        string='Average Marks',
        compute='_compute_statistics',
        store=True
    )
    
    attainment_percentage = fields.Float(
        string='Attainment %',
        compute='_compute_statistics',
        store=True
    )
    
    # Additional Information
    solution = fields.Html(string='Solution/Answer Key')
    rubric = fields.Html(string='Grading Rubric')
    hints = fields.Text(string='Hints')
    
    active = fields.Boolean(default=True)
    
    @api.depends('assessment_id', 'question_number')
    def _compute_name(self):
        for record in self:
            if record.assessment_id and record.question_number:
                record.name = f"{record.assessment_id.name} - Q{record.question_number}"
            else:
                record.name = 'New Question'
    
    @api.depends('answer_ids.marks_obtained')
    def _compute_statistics(self):
        for record in self:
            if record.answer_ids:
                total_obtained = sum(record.answer_ids.mapped('marks_obtained'))
                record.average_marks_obtained = total_obtained / len(record.answer_ids)
                record.attainment_percentage = (total_obtained / (len(record.answer_ids) * record.marks)) * 100
            else:
                record.average_marks_obtained = 0.0
                record.attainment_percentage = 0.0
    
    @api.constrains('marks')
    def _check_marks(self):
        for record in self:
            if record.marks <= 0:
                raise ValidationError(_('Question marks must be positive.'))
    
    @api.constrains('assessment_id')
    def _check_total_marks(self):
        """Validate that sum of question marks equals assessment total marks"""
        for record in self:
            if record.assessment_id and record.assessment_id.state == 'finalized':
                total_questions = sum(record.assessment_id.question_ids.mapped('marks'))
                if abs(total_questions - record.assessment_id.total_marks) > 0.01:
                    raise ValidationError(
                        _('Sum of question marks (%.2f) must equal assessment total marks (%.2f)') %
                        (total_questions, record.assessment_id.total_marks)
                    )
    
    _sql_constraints = [
        ('unique_question_number_per_assessment',
         'UNIQUE(assessment_id, question_number)',
         'Question number must be unique within an assessment!')
    ]


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
    
    # Marks
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
    
    _sql_constraints = [
        ('unique_student_assessment',
         'UNIQUE(assessment_id, student_id)',
         'Student can have only one result per assessment!')
    ]


class OBEAssessmentAnswer(models.Model):
    """Student answers for individual questions"""
    _name = 'obe.assessment.answer'
    _description = 'OBE Assessment Answer'

    result_id = fields.Many2one(
        'obe.assessment.result',
        string='Result',
        
        ondelete='cascade'
    )
    
    question_id = fields.Many2one(
        'obe.assessment.question',
        string='Question',
        
        ondelete='cascade'
    )
    
    student_id = fields.Many2one(
        related='result_id.student_id',
        string='Student',
        store=True,
        readonly=True
    )
    
    marks_obtained = fields.Float(
        string='Marks Obtained',
        
        default=0.0
    )
    
    max_marks = fields.Float(
        related='question_id.marks',
        string='Max Marks',
        readonly=True
    )
    
    answer_text = fields.Html(string='Student Answer')
    
    is_correct = fields.Boolean(
        string='Correct',
        compute='_compute_is_correct',
        store=True
    )
    
    feedback = fields.Text(string='Feedback')
    
    @api.depends('marks_obtained', 'max_marks')
    def _compute_is_correct(self):
        for record in self:
            record.is_correct = record.marks_obtained >= (record.max_marks * 0.6)  # 60% threshold
    
    @api.constrains('marks_obtained', 'max_marks')
    def _check_marks_obtained(self):
        for record in self:
            if record.marks_obtained < 0 or record.marks_obtained > record.max_marks:
                raise ValidationError(
                    _('Marks obtained must be between 0 and %.2f') % record.max_marks
                )
    
    _sql_constraints = [
        ('unique_result_question',
         'UNIQUE(result_id, question_id)',
         'Student can have only one answer per question!')
    ]


class OBECLOAttainment(models.Model):
    """
    FR-012: CLO Attainment Calculation - Direct Method
    Automatically calculate CLO attainment based on student performance
    """
    _name = 'obe.clo.attainment'
    _description = 'CLO Attainment (Direct Method)'
    _order = 'course_offering_id, clo_id'

    course_offering_id = fields.Many2one(
        'obe.course.offering',
        string='Course Offering',
        
        ondelete='cascade'
    )
    
    clo_id = fields.Many2one(
        'obe.clo',
        string='CLO',
        
        ondelete='cascade'
    )
    
    assessment_id = fields.Many2one(
        'obe.assessment',
        string='Assessment',
        help='Specific assessment (if calculated per assessment)'
    )
    
    # Calculation Parameters
    total_students = fields.Integer(string='Total Students')
    students_passed = fields.Integer(string='Students Passed')
    
    # Attainment Results
    attainment_percentage = fields.Float(
        string='Attainment %',
        help='(Students Passed / Total Students) × 100'
    )
    
    attainment_level = fields.Selection([
        ('not_attained', 'Not Attained (< 60%)'),
        ('partially_attained', 'Partially Attained (60-75%)'),
        ('attained', 'Attained (75-90%)'),
        ('highly_attained', 'Highly Attained (> 90%)')
    ], string='Attainment Level', compute='_compute_attainment_level', store=True)
    
    # Threshold
    passing_threshold = fields.Float(
        string='Passing Threshold %',
        default=60.0,
        help='Minimum percentage to consider a student as passed'
    )
    
    # Student-wise Details
    student_detail_ids = fields.One2many(
        'obe.clo.attainment.detail',
        'attainment_id',
        string='Student Details'
    )
    
    # Statistics
    average_marks = fields.Float(string='Average Marks')
    highest_marks = fields.Float(string='Highest Marks')
    lowest_marks = fields.Float(string='Lowest Marks')
    
    calculation_date = fields.Datetime(
        string='Calculation Date',
        default=fields.Datetime.now
    )
    
    calculated_by = fields.Many2one(
        'res.users',
        string='Calculated By',
        default=lambda self: self.env.user
    )
    
    remarks = fields.Text(string='Remarks')
    
    @api.depends('attainment_percentage')
    def _compute_attainment_level(self):
        for record in self:
            percentage = record.attainment_percentage
            if percentage < 60:
                record.attainment_level = 'not_attained'
            elif percentage < 75:
                record.attainment_level = 'partially_attained'
            elif percentage < 90:
                record.attainment_level = 'attained'
            else:
                record.attainment_level = 'highly_attained'
    
    @api.model
    def calculate_clo_attainment(self, clo_id, offering_id, assessment_id=None):
        """
        Calculate CLO attainment for a specific CLO and offering
        Can be calculated for all assessments or a specific assessment
        """
        clo = self.env['obe.clo'].browse(clo_id)
        offering = self.env['obe.course.offering'].browse(offering_id)
        
        # Get questions mapped to this CLO
        domain = [('clo_id', '=', clo_id)]
        if assessment_id:
            domain.append(('assessment_id', '=', assessment_id))
        else:
            domain.append(('assessment_id.course_offering_id', '=', offering_id))
        
        questions = self.env['obe.assessment.question'].search(domain)
        
        if not questions:
            _logger.warning(f"No questions found for CLO {clo_id} in offering {offering_id}")
            return None
        
        # Get all students enrolled in the offering
        enrollments = self.env['obe.enrollment'].search([
            ('course_offering_id', '=', offering_id)
        ])
        
        total_students = len(enrollments)
        if total_students == 0:
            return None
        
        # Calculate student-wise performance
        student_scores = {}
        for enrollment in enrollments:
            student_id = enrollment.student_id.id
            total_obtained = 0.0
            total_max = 0.0
            
            for question in questions:
                answer = self.env['obe.assessment.answer'].search([
                    ('question_id', '=', question.id),
                    ('student_id', '=', student_id)
                ], limit=1)
                
                if answer:
                    total_obtained += answer.marks_obtained
                    total_max += question.marks
            
            if total_max > 0:
                percentage = (total_obtained / total_max) * 100
                student_scores[student_id] = {
                    'obtained': total_obtained,
                    'max': total_max,
                    'percentage': percentage
                }
        
        # Calculate attainment
        passing_threshold = 60.0  # Can be made configurable
        students_passed = sum(1 for score in student_scores.values() 
                            if score['percentage'] >= passing_threshold)
        
        attainment_percentage = (students_passed / total_students) * 100 if total_students > 0 else 0
        
        # Statistics
        percentages = [score['percentage'] for score in student_scores.values()]
        average_marks = sum(percentages) / len(percentages) if percentages else 0
        highest_marks = max(percentages) if percentages else 0
        lowest_marks = min(percentages) if percentages else 0
        
        # Create or update attainment record
        existing = self.search([
            ('clo_id', '=', clo_id),
            ('course_offering_id', '=', offering_id),
            ('assessment_id', '=', assessment_id if assessment_id else False)
        ], limit=1)
        
        vals = {
            'clo_id': clo_id,
            'course_offering_id': offering_id,
            'assessment_id': assessment_id,
            'total_students': total_students,
            'students_passed': students_passed,
            'attainment_percentage': attainment_percentage,
            'passing_threshold': passing_threshold,
            'average_marks': average_marks,
            'highest_marks': highest_marks,
            'lowest_marks': lowest_marks,
            'calculation_date': fields.Datetime.now(),
            'calculated_by': self.env.user.id
        }
        
        if existing:
            attainment = existing
            attainment.write(vals)
        else:
            attainment = self.create(vals)
        
        # Create student detail records
        attainment.student_detail_ids.unlink()
        detail_vals = []
        for student_id, score in student_scores.items():
            detail_vals.append({
                'attainment_id': attainment.id,
                'student_id': student_id,
                'marks_obtained': score['obtained'],
                'total_marks': score['max'],
                'percentage': score['percentage'],
                'is_passed': score['percentage'] >= passing_threshold
            })
        
        if detail_vals:
            self.env['obe.clo.attainment.detail'].create(detail_vals)
        
        return attainment


class OBECLOAttainmentDetail(models.Model):
    """Student-wise CLO attainment details"""
    _name = 'obe.clo.attainment.detail'
    _description = 'CLO Attainment Detail'

    attainment_id = fields.Many2one(
        'obe.clo.attainment',
        string='Attainment',
        
        ondelete='cascade'
    )
    
    student_id = fields.Many2one(
        'obe.student',
        string='Student',
        required=True
    )
    
    marks_obtained = fields.Float(string='Marks Obtained')
    total_marks = fields.Float(string='Total Marks')
    percentage = fields.Float(string='Percentage')
    is_passed = fields.Boolean(string='Passed')


class OBEPLOAttainment(models.Model):
    """
    FR-013: PLO Attainment Calculation
    Calculate PLO attainment by aggregating CLO attainments
    """
    _name = 'obe.plo.attainment'
    _description = 'PLO Attainment'
    _order = 'academic_year desc, plo_id'

    plo_id = fields.Many2one(
        'obe.plo',
        string='PLO',
        
        ondelete='cascade'
    )
    
    program_id = fields.Many2one(
        related='plo_id.program_id',
        string='Program',
        store=True,
        readonly=True
    )
    
    academic_year = fields.Char(
        string='Academic Year',
        
        help='e.g., 2024-2025'
    )
    
    # Attainment Results
    attainment_percentage = fields.Float(
        string='PLO Attainment %',
        help='Weighted average of contributing CLO attainments'
    )
    
    attainment_level = fields.Selection([
        ('not_attained', 'Not Attained (< 60%)'),
        ('partially_attained', 'Partially Attained (60-75%)'),
        ('attained', 'Attained (75-90%)'),
        ('highly_attained', 'Highly Attained (> 90%)')
    ], string='Attainment Level', compute='_compute_attainment_level', store=True)
    
    # Contributing Courses
    contributing_course_ids = fields.One2many(
        'obe.plo.attainment.course',
        'plo_attainment_id',
        string='Contributing Courses'
    )
    
    # Statistics
    total_contributing_courses = fields.Integer(
        compute='_compute_statistics',
        store=True
    )
    
    calculation_date = fields.Datetime(
        string='Calculation Date',
        default=fields.Datetime.now
    )
    
    calculated_by = fields.Many2one(
        'res.users',
        string='Calculated By',
        default=lambda self: self.env.user
    )
    
    remarks = fields.Text(string='Remarks')
    
    @api.depends('attainment_percentage')
    def _compute_attainment_level(self):
        for record in self:
            percentage = record.attainment_percentage
            if percentage < 60:
                record.attainment_level = 'not_attained'
            elif percentage < 75:
                record.attainment_level = 'partially_attained'
            elif percentage < 90:
                record.attainment_level = 'attained'
            else:
                record.attainment_level = 'highly_attained'
    
    @api.depends('contributing_course_ids')
    def _compute_statistics(self):
        for record in self:
            record.total_contributing_courses = len(record.contributing_course_ids)
    
    @api.model
    def calculate_plo_attainment(self, plo_id, academic_year):
        """
        Calculate PLO attainment using formula:
        PLO = Σ(CLO_Attain × Strength × Credit) / Σ(Strength × Credit)
        """
        plo = self.env['obe.plo'].browse(plo_id)
        
        # Get all CLO-PLO mappings for this PLO
        mappings = self.env['obe.clo.plo.mapping'].search([
            ('plo_id', '=', plo_id)
        ])
        
        if not mappings:
            _logger.warning(f"No CLO-PLO mappings found for PLO {plo_id}")
            return None
        numerator = 0.0
        denominator = 0.0
        course_contributions = {}
        
        for mapping in mappings:
            clo = mapping.clo_id
            course = clo.course_id
            strength = mapping.strength
            credits = course.credits or 3.0
            offerings = self.env['obe.course.offering'].search([
                ('course_id', '=', course.id),
            ])
            
            clo_attainments = self.env['obe.clo.attainment'].search([
                ('clo_id', '=', clo.id),
                ('course_offering_id', 'in', offerings.ids)
            ])
            
            if clo_attainments:
                avg_clo_attainment = sum(clo_attainments.mapped('attainment_percentage')) / len(clo_attainments)
                
                weight = strength * credits
                contribution = avg_clo_attainment * weight
                
                numerator += contribution
                denominator += weight
                
                if course.id not in course_contributions:
                    course_contributions[course.id] = {
                        'course': course,
                        'credits': credits,
                        'clo_count': 0,
                        'total_contribution': 0.0,
                        'weighted_attainment': 0.0
                    }
                
                course_contributions[course.id]['clo_count'] += 1
                course_contributions[course.id]['total_contribution'] += contribution
                course_contributions[course.id]['weighted_attainment'] = (
                    course_contributions[course.id]['total_contribution'] / weight
                )

        plo_attainment_pct = (numerator / denominator * 100) if denominator > 0 else 0
        existing = self.search([
            ('plo_id', '=', plo_id),
            ('academic_year', '=', academic_year)
        ], limit=1)
        
        vals = {
            'plo_id': plo_id,
            'academic_year': academic_year,
            'attainment_percentage': plo_attainment_pct,
            'calculation_date': fields.Datetime.now(),
            'calculated_by': self.env.user.id
        }
        
        if existing:
            plo_attainment = existing
            plo_attainment.write(vals)
        else:
            plo_attainment = self.create(vals)
        
        # Create contributing course records
        plo_attainment.contributing_course_ids.unlink()
        course_vals = []
        for course_id, data in course_contributions.items():
            course_vals.append({
                'plo_attainment_id': plo_attainment.id,
                'course_id': course_id,
                'credits': data['credits'],
                'clo_count': data['clo_count'],
                'contribution_percentage': data['weighted_attainment']
            })
        
        if course_vals:
            self.env['obe.plo.attainment.course'].create(course_vals)
        
        return plo_attainment


class OBEPLOAttainmentCourse(models.Model):
    """Course-wise contribution to PLO attainment"""
    _name = 'obe.plo.attainment.course'
    _description = 'PLO Attainment - Course Contribution'

    plo_attainment_id = fields.Many2one(
        'obe.plo.attainment',
        string='PLO Attainment',
        
        ondelete='cascade'
    )
    
    course_id = fields.Many2one(
        'obe.course',
        string='Course',
        required=True
    )
    
    credits = fields.Float(string='Credits')
    clo_count = fields.Integer(string='Contributing CLOs')
    contribution_percentage = fields.Float(string='Contribution %')