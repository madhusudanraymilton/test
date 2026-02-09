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


    question_line_ids = fields.One2many(
        'assessment.question.line', 
        'assessment_id', 
        string='Questions'
    )
    
    assessment_type = fields.Selection([
    ('class_participation', 'Class Participation'),
    ('class_test', 'Class Tests (Impromptu Quizzes)'),
    ('midterm', 'Midterm Assessment'),
    ('final_exam', 'Final Exam'),
    ('term_paper', 'Term Paper'),
    ('assignment', 'Assignment (Business Process Modelling)'),
    ('case_study', 'Case Study (Educational Institution, Technology Company)')
    ], string='Assessment Type', tracking=True)

    

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
    

    total_marks = fields.Float(
        string='Marks',
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
    




class AssessmentQuestionLine(models.Model):

    _name = 'assessment.question.line'
    _description = 'Assessment Question Line'
  


  
    
    assessment_id = fields.Many2one(
        'obe.assessment',
        string='Assessment',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    question_id = fields.Many2one(
        'obe.assessment.question',
        string='Question',
        required=True,
        ondelete='restrict',
        domain="[('assessment_id', '=', assessment_id)]"
    )


    question_number = fields.Char(
        related='question_id.question_number',
        string='Question No.',
        store=True,
        readonly=True
    )
    
    question_text = fields.Text(
        related='question_id.question_text',
        string='Question',
        readonly=True
    )
    
    marks = fields.Float(
        related='question_id.marks',
        string='Marks',
        store=True,
        readonly=True
    )
    
    clo_id = fields.Many2one(
        related='question_id.clo_id',
        string='CLO',
        store=True,
        readonly=True
    )
    
    bloom_level = fields.Selection(
        related='question_id.bloom_level',
        string='Bloom Level',
        store=True,
        readonly=True
    )

    is_mandatory = fields.Boolean(
        string='Mandatory',
        default=True,
        help='If unchecked, this question is optional for students'
    )
    
    is_bonus = fields.Boolean(
        string='Bonus Question',
        default=False,
        help='Marks will be added as bonus, not counted in total'
    )
    
    weightage_override = fields.Float(
        string='Weightage Override (%)',
        help='Override default question weightage within this assessment'
    )
    
    notes = fields.Text(
        string='Instructions/Notes',
        help='Special instructions for this question in this assessment'
    )
    
    # State
    active = fields.Boolean(
        default=True
    )
    
  
    
    @api.constrains('weightage_override')
    def _check_weightage_override(self):
        """Validate weightage override is within valid range"""
        for record in self:
            if record.weightage_override and (
                record.weightage_override < 0 or record.weightage_override > 100
            ):
                raise ValidationError(
                    _('Weightage override must be between 0 and 100%.')
                )
    
    @api.onchange('question_id')
    def _onchange_question_id(self):
        """Auto-populate sequence based on question number"""
        if self.question_id and self.question_id.question_number:
            try:
                # Try to extract numeric part for sequence
                num = ''.join(filter(str.isdigit, self.question_id.question_number))
                if num:
                    self.sequence = int(num) * 10
            except (ValueError, AttributeError):
                pass
    
    def name_get(self):
        """Custom display name"""
        result = []
        for record in self:
            name = f"{record.assessment_id.name} - {record.question_number or 'Q-?'}"
            result.append((record.id, name))
        return result
    
    @api.model
    def create(self, vals):
        """Validate before creating"""
        record = super().create(vals)
        record._validate_assessment_state()
        return record
    
    def write(self, vals):
        """Validate before updating"""
        res = super().write(vals)
        self._validate_assessment_state()
        return res
    
    def _validate_assessment_state(self):
        """Prevent modifications when assessment is finalized"""
        for record in self:
            if record.assessment_id.state == 'finalized':
                raise ValidationError(
                    _('Cannot modify questions for a finalized assessment.')
                )