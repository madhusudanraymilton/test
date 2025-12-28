# -*- coding: utf-8 -*-
###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StudentStudent(models.Model):
    """Extend WK School student with library features"""
    _inherit = 'student.student'

    # Library card relationship
    library_card_id = fields.Many2one('op.library.card', string='Library Card',
                                       domain=[('type', '=', 'student')], ondelete='restrict')
    
    # Book movements
    media_movement_ids = fields.One2many(
        'op.media.movement',
        'wk_student_id',
        string='Book Movements',
        help="All books borrowed by this student"
    )
    
    # Statistics - computed fields
    media_movement_count = fields.Integer(
        'Total Movements',
        compute='_compute_library_stats',
        store=True,
        help="Total number of book transactions"
    )
    outstanding_books_count = fields.Integer(
        'Books Issued',
        compute='_compute_library_stats',
        store=True,
        help="Books currently borrowed"
    )
    overdue_books_count = fields.Integer(
        'Overdue Books',
        compute='_compute_library_stats',
        store=True,
        help="Books not returned on time"
    )
    total_penalty_amount = fields.Float(
        'Total Penalty',
        compute='_compute_library_stats',
        store=True,
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
                if movement.return_date and movement.library_card_id and movement.library_card_id.library_card_type_id:
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
        """Create library card using wk_student_id"""
        self.ensure_one()
        card = self.env['op.library.card'].create({
            'type': 'student',
            'wk_student_id': self.id,  # Use wk_student_id instead of student_id
            'library_card_type_id': self.env.ref('openeducat_library.op_library_card_type_1').id,
        })
        self.library_card_id = card.id
        return self.action_view_library_card()
    
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
            'domain': [('wk_student_id', '=', self.id)],
            'context': {
                'default_wk_student_id': self.id,
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
                'default_wk_student_id': self.id,
                'default_type': 'student',
            }
        }


class OpLibraryCard(models.Model):
    """Extend library card to support WK School students"""
    _inherit = 'op.library.card'

    wk_student_id = fields.Many2one(
        'student.student',
        string='WK Student',
        domain=[('library_card_id', '=', False)]
    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            if record.type == 'student' and record.wk_student_id:
                record.wk_student_id.library_card_id = record
        return res

    @api.onchange('wk_student_id')
    def onchange_wk_student(self):
        if self.wk_student_id:
            self.partner_id = self.wk_student_id.partner_id.id if self.wk_student_id.partner_id else False
        
    @api.onchange('student_id')
    def onchange_student_clear_wk(self):
        """Clear wk_student_id when openeducat student is selected"""
        if self.student_id:
            self.wk_student_id = False


class OpMediaMovement(models.Model):
    """Extend media movement to support WK School students"""
    _inherit = 'op.media.movement'

    wk_student_id = fields.Many2one(
        'student.student',
        string='WK Student'
    )
    
    # Computed field for overdue status
    is_overdue = fields.Boolean(
        compute='_compute_is_overdue',
        string='Is Overdue',
        store=True
    )
    
    days_overdue = fields.Integer(
        compute='_compute_days_overdue',
        string='Days Overdue',
        store=True
    )

    @api.depends('return_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for movement in self:
            movement.is_overdue = (
                movement.state == 'issue' and 
                movement.return_date and 
                movement.return_date < today
            )

    @api.depends('return_date', 'state')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for movement in self:
            if movement.state == 'issue' and movement.return_date and movement.return_date < today:
                movement.days_overdue = (today - movement.return_date).days
            else:
                movement.days_overdue = 0

    @api.onchange('wk_student_id')
    def onchange_wk_student_id(self):
        if self.wk_student_id:
            self.library_card_id = self.wk_student_id.library_card_id.id if self.wk_student_id.library_card_id else False
            self.partner_id = self.wk_student_id.partner_id.id if self.wk_student_id.partner_id else False
            self.user_id = self.wk_student_id.user_id.id if self.wk_student_id.user_id else False

    def action_return_book(self):
        """Quick action to return a book"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Return Book',
            'res_model': 'return.media',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_media_id': self.media_id.id,
                'default_media_unit_id': self.media_unit_id.id,
            }
        }