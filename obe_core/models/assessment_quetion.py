# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class OBEAssessmentQuestion(models.Model):
    """
    FR-011: Question-Level CLO Mapping
    Supports granular question-level CLO mapping for comprehensive attainment tracking
    """
    _name = 'obe.assessment.question'
    _description = 'OBE Assessment Question'
    _order = 'assessment_id, sequence, question_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'question_number'

    name = fields.Char(
        string='Question Reference',
        compute='_compute_name',
        store=True
    )
    
    assessment_id = fields.Many2one(
        'obe.assessment',
        string='Assessment',
        required=True,  
        ondelete='cascade',
        tracking=True
    )
    
    sequence = fields.Integer(string='Sequence', default=10)
    
    question_number = fields.Char(
        string='Question Number',
        required=True,
        help='Question identifier (e.g., Q1, 1a, 2.1)',
        tracking=True
    )
    
    question_text = fields.Text(
        string='Question Text',
        required=True
    )
    
    marks = fields.Float(
        string='Marks',
        required=True,
        default=1.0,
        help='Maximum marks for this question'
    )
    
    clo_id = fields.Many2one(
        'obe.clo',
        string='Assigned CLO', # Fixed spelling
        help='Course Learning Outcome assessed by this question',
        tracking=True
    )
    
    bloom_level = fields.Selection([
        ('remember', 'Remember'),
        ('understand', 'Understand'),
        ('apply', 'Apply'),
        ('analyze', 'Analyze'),
        ('evaluate', 'Evaluate'),
        ('create', 'Create')
    ], string='Bloom Level', required=True, tracking=True)
    
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
    
    solution = fields.Html(string='Solution/Answer Key')
    rubric = fields.Html(string='Grading Rubric')
    hints = fields.Text(string='Hints')
    active = fields.Boolean(default=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active')
    ], string="Status", default='draft', tracking=True)

    @api.depends('assessment_id.name', 'question_number')
    def _compute_name(self):
        for record in self:
            if record.assessment_id and record.question_number:
                record.name = f"{record.assessment_id.name} - {record.question_number}"
            else:
                record.name = _('New Question')

    @api.depends('answer_ids.marks_obtained', 'marks')
    def _compute_statistics(self):
        for record in self:
            if record.answer_ids and record.marks > 0:
                total_obtained = sum(record.answer_ids.mapped('marks_obtained'))
                count = len(record.answer_ids)
                record.average_marks_obtained = total_obtained / count
                # Calculate attainment: (Avg Marks / Max Marks) * 100
                record.attainment_percentage = (record.average_marks_obtained / record.marks) * 100
            else:
                record.average_marks_obtained = 0.0
                record.attainment_percentage = 0.0

    @api.constrains('marks')
    def _check_marks(self):
        for record in self:
            if record.marks <= 0:
                raise ValidationError(_('Question marks must be a positive value.'))

    @api.constrains('assessment_id', 'marks')
    def _check_total_marks(self):
        """Validate that sum of question marks matches assessment total marks when finalized"""
        for record in self:
            # We only enforce this strict check if the parent assessment is being finalized
            if record.assessment_id and record.assessment_id.state == 'finalized':
                total_questions_marks = sum(record.assessment_id.question_ids.mapped('marks'))
                if abs(total_questions_marks - record.assessment_id.total_marks) > 0.01:
                    raise ValidationError(
                        _('Total marks mismatch! Sum of questions (%.2f) must equal assessment total (%.2f).') %
                        (total_questions_marks, record.assessment_id.total_marks)
                    )

    def action_active(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only Draft questions can be activated."))
            rec.state = 'active'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'