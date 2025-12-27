# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StudentStudent(models.Model):
    """Extend WK School student with library features"""
    _inherit = 'student.student'

    # Library card relationship
    library_card_id = fields.Many2one(
        'op.library.card',
        string='Library Card',
        readonly=True,
        help="Library card issued to this student"
    )
    
    # Book movements
    media_movement_ids = fields.One2many(
        'op.media.movement',
        'student_id',
        string='Book Movements',
        help="All books borrowed by this student"
    )
    
    # Statistics - computed fields
    media_movement_count = fields.Integer(
        'Total Movements',
        compute='_compute_library_stats',
        help="Total number of book transactions"
    )
    outstanding_books_count = fields.Integer(
        'Books Issued',
        compute='_compute_library_stats',
        help="Books currently borrowed"
    )
    overdue_books_count = fields.Integer(
        'Overdue Books',
        compute='_compute_library_stats',
        help="Books not returned on time"
    )
    total_penalty_amount = fields.Float(
        'Total Penalty',
        compute='_compute_library_stats',
        help="Total penalty amount owed"
    )
    library_status = fields.Selection([
        ('good', 'Good Standing'),
        ('warning', 'Has Overdue'),
        ('blocked', 'Blocked')
    ], string='Library Status', compute='_compute_library_status', store=True)

    @api.depends('media_movement_ids', 'media_movement_ids.state', 'media_movement_ids.return_date')
    def _compute_library_stats(self):
        """Compute all library statistics"""
        today = fields.Date.today()
        
        for student in self:
            movements = student.media_movement_ids
            student.media_movement_count = len(movements)
            
            issued = movements.filtered(lambda m: m.state == 'issue')
            student.outstanding_books_count = len(issued)
            
            overdue = issued.filtered(lambda m: m.return_date and m.return_date < today)
            student.overdue_books_count = len(overdue)
            
            # Calculate total penalty
            penalty = 0.0
            for movement in overdue:
                if movement.return_date:
                    days_late = (today - movement.return_date).days
                    penalty_per_day = movement.library_card_id.library_card_type_id.penalty_amt_per_day
                    penalty += days_late * penalty_per_day
            student.total_penalty_amount = penalty

    @api.depends('overdue_books_count', 'outstanding_books_count')
    def _compute_library_status(self):
        """Determine library status"""
        for student in self:
            if student.overdue_books_count > 5:
                student.library_status = 'blocked'
            elif student.overdue_books_count > 0:
                student.library_status = 'warning'
            else:
                student.library_status = 'good'

    # Actions
    def action_create_library_card(self):
        """Open wizard to create library card"""
        self.ensure_one()
        
        if self.library_card_id:
            raise ValidationError(_('This student already has a library card: %s') % self.library_card_id.number)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Library Card',
            'res_model': 'op.library.card',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_type': 'student',
                'default_student_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_company_id': self.company_id.id,
            }
        }

    def action_view_library_card(self):
        """View existing library card"""
        self.ensure_one()
        
        if not self.library_card_id:
            raise ValidationError(_('This student does not have a library card yet.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Library Card',
            'res_model': 'op.library.card',
            'view_mode': 'form',
            'res_id': self.library_card_id.id,
            'target': 'current',
        }

    def action_view_book_movements(self):
        """View all book movements"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Book Movements - %s') % self.name,
            'res_model': 'op.media.movement',
            'view_mode': 'tree,form',
            'domain': [('student_id', '=', self.id)],
            'context': {
                'default_student_id': self.id,
                'default_library_card_id': self.library_card_id.id if self.library_card_id else False,
                'default_type': 'student',
            }
        }

    def action_issue_book(self):
        """Quick action to issue a book"""
        self.ensure_one()
        
        if not self.library_card_id:
            raise ValidationError(_('Create a library card first before issuing books.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Issue Book',
            'res_model': 'op.media.movement',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_library_card_id': self.library_card_id.id,
                'default_student_id': self.id,
                'default_type': 'student',
                'default_state': 'issue',
            }
        }


class HrEmployee(models.Model):
    """Extend HR Employee for faculty library access"""
    _inherit = 'hr.employee'

    library_card_id = fields.Many2one(
        'op.library.card',
        string='Library Card',
        readonly=True
    )
    media_movement_ids = fields.One2many(
        'op.media.movement',
        'faculty_id',
        string='Book Movements'
    )
    media_movement_count = fields.Integer(
        'Books Borrowed',
        compute='_compute_media_count'
    )

    @api.depends('media_movement_ids')
    def _compute_media_count(self):
        for employee in self:
            employee.media_movement_count = len(employee.media_movement_ids)

    def action_create_library_card(self):
        """Create library card for faculty"""
        self.ensure_one()
        
        if self.library_card_id:
            raise ValidationError(_('This faculty already has a library card.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Library Card',
            'res_model': 'op.library.card',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_type': 'faculty',
                'default_faculty_id': self.id,
                'default_partner_id': self.user_id.partner_id.id if self.user_id else False,
            }
        }

    def action_view_book_movements(self):
        """View faculty book movements"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Book Movements',
            'res_model': 'op.media.movement',
            'view_mode': 'tree,form',
            'domain': [('faculty_id', '=', self.id)],
        }