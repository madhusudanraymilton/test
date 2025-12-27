###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<https://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpLibraryCardType(models.Model):
    _name = "op.library.card.type"
    _description = "Library Card Type"

    name = fields.Char('Name', required=True)
    allow_media = fields.Integer('No Of Books Allowed', default=10, required=True)
    duration = fields.Integer('Duration (Days)', help='Loan duration in days', required=True)
    penalty_amt_per_day = fields.Float('Penalty Amount Per Day', required=True)

    @api.constrains('allow_media', 'duration', 'penalty_amt_per_day')
    def check_details(self):
        for rec in self:
            if rec.allow_media < 0 or rec.duration < 0.0 or rec.penalty_amt_per_day < 0.0:
                raise ValidationError(_('All values must be positive'))


class OpLibraryCard(models.Model):
    _name = "op.library.card"
    _rec_name = "number"
    _description = "Library Card"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Core fields
    number = fields.Char('Card Number', readonly=True, copy=False, tracking=True)
    library_card_type_id = fields.Many2one('op.library.card.type', 'Card Type', required=True, tracking=True)
    issue_date = fields.Date('Issue Date', required=True, default=fields.Date.today, tracking=True)
    type = fields.Selection([
        ('student', 'Student'),
        ('faculty', 'Faculty')
    ], 'Type', default='student', required=True, tracking=True)
    active = fields.Boolean(default=True)

    # Integration with WK School Management
    student_id = fields.Many2one(
        'student.student',  # WK School student model
        'Student',
        domain="[('library_card_id', '=', False)]",
        help="WK School Management student"
    )
    
    # Integration with HR (for faculty)
    faculty_id = fields.Many2one(
        'hr.employee',
        'Faculty',
        domain="[('library_card_id', '=', False)]",
        help="Faculty member"
    )
    
    # Computed partner field
    partner_id = fields.Many2one(
        'res.partner',
        'Person',
        compute='_compute_partner_id',
        store=True,
        readonly=False
    )
    
    # Additional integration fields
    company_id = fields.Many2one(
        'res.company',
        'School',
        default=lambda self: self.env.company,
        required=True
    )
    current_grade_id = fields.Many2one(
        'wk.school.grade',
        related='student_id.current_grade_id',
        string='Current Grade',
        store=True
    )
    
    # Statistics
    media_movement_count = fields.Integer(
        'Total Movements',
        compute='_compute_movement_stats'
    )
    outstanding_books = fields.Integer(
        'Books Issued',
        compute='_compute_movement_stats'
    )
    overdue_books = fields.Integer(
        'Overdue Books',
        compute='_compute_movement_stats'
    )

    _sql_constraints = [
        ('unique_library_card_number', 'unique(number)', 'Library card number must be unique!')
    ]

    @api.depends('student_id', 'faculty_id')
    def _compute_partner_id(self):
        """Auto-populate partner based on student or faculty"""
        for card in self:
            if card.student_id:
                card.partner_id = card.student_id.partner_id
            elif card.faculty_id:
                card.partner_id = card.faculty_id.user_id.partner_id if card.faculty_id.user_id else False
            else:
                card.partner_id = False

    @api.depends('student_id', 'faculty_id')
    def _compute_movement_stats(self):
        """Compute book statistics"""
        Movement = self.env['op.media.movement']
        today = fields.Date.today()
        
        for card in self:
            movements = Movement.search([('library_card_id', '=', card.id)])
            card.media_movement_count = len(movements)
            card.outstanding_books = len(movements.filtered(lambda m: m.state == 'issue'))
            card.overdue_books = len(movements.filtered(
                lambda m: m.state == 'issue' and m.return_date and m.return_date < today
            ))

    @api.model_create_multi
    def create(self, vals_list):
        """Generate card number and link to student/faculty"""
        for vals in vals_list:
            if not vals.get('number'):
                vals['number'] = self.env['ir.sequence'].next_by_code('op.library.card') or '/'
        
        cards = super().create(vals_list)
        
        # Link back to student or faculty
        for card in cards:
            if card.type == 'student' and card.student_id:
                card.student_id.library_card_id = card.id
            elif card.type == 'faculty' and card.faculty_id:
                card.faculty_id.library_card_id = card.id
        
        return cards

    @api.onchange('type')
    def onchange_type(self):
        """Clear selections when type changes"""
        self.student_id = False
        self.faculty_id = False
        self.partner_id = False

    def action_view_movements(self):
        """Smart button to view all book movements"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Book Movements',
            'res_model': 'op.media.movement',
            'view_mode': 'tree,form',
            'domain': [('library_card_id', '=', self.id)],
            'context': {'default_library_card_id': self.id}
        }