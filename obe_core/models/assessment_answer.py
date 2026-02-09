# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class OBEAssessmentAnswer(models.Model):
    """
    Individual question answers for student results
    """
    _name = 'obe.assessment.answer'
    _description = 'OBE Assessment Answer'
    _order = 'result_id, question_id'
    
    # Basic Information
    result_id = fields.Many2one(
        'obe.assessment.result',
        string='Result',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    question_id = fields.Many2one(
        'obe.assessment.question',
        string='Question',
        required=True,
        ondelete='restrict',
        index=True
    )
    
    # Student Answer
    answer_text = fields.Text(
        string='Answer',
        help='Student answer text'
    )
    
    # Marks
    marks_obtained = fields.Float(
        string='Marks Obtained',
        default=0.0
    )
    
    max_marks = fields.Float(
        string='Maximum Marks',
        related='question_id.marks',
        store=True,
        readonly=True
    )
    
    is_correct = fields.Boolean(
        string='Correct',
        compute='_compute_is_correct',
        store=True
    )
    
    # Feedback
    feedback = fields.Text(
        string='Feedback',
        help='Grader feedback for this answer'
    )
    
    active = fields.Boolean(default=True)
    
    # SQL Constraints
    _sql_constraints = [
        (
            'unique_result_question',
            'UNIQUE(result_id, question_id)',
            'Each question can only be answered once per result!'
        )
    ]
    
    @api.depends('marks_obtained', 'max_marks')
    def _compute_is_correct(self):
        for record in self:
            if record.max_marks > 0:
                # Consider >60% as correct
                record.is_correct = (record.marks_obtained / record.max_marks) >= 0.6
            else:
                record.is_correct = False
    
    @api.constrains('marks_obtained', 'max_marks')
    def _check_marks(self):
        for record in self:
            if record.marks_obtained < 0:
                raise ValidationError(_('Marks obtained cannot be negative.'))
            if record.marks_obtained > record.max_marks:
                raise ValidationError(
                    _('Marks obtained (%.2f) cannot exceed maximum marks (%.2f).') %
                    (record.marks_obtained, record.max_marks)
                )