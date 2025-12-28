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

    name = fields.Char('Name', size=256, required=True)
    allow_media = fields.Integer('No Of Medias Allowed', default=10,
                                 required=True)
    duration = fields.Integer(
        'Duration', help='Duration in terms of Number of Lead Days',
        required=True)
    penalty_amt_per_day = fields.Float('Penalty Amount Per Day',
                                       required=True)

    @api.constrains('allow_media', 'duration', 'penalty_amt_per_day')
    def check_details(self):
        if self.allow_media < 0 or self.duration < 0.0 or \
                self.penalty_amt_per_day < 0.0:
            raise ValidationError(_('Enter proper value'))


class OpLibraryCard(models.Model):
    _name = "op.library.card"
    _rec_name = "number"
    _description = "Library Card"

    partner_id = fields.Many2one(
        'res.partner', 'Student/Faculty', required=False)
    number = fields.Char('Number', size=256, readonly=True)
    library_card_type_id = fields.Many2one(
        'op.library.card.type', 'Card Type', required=True)
    issue_date = fields.Date(
        'Issue Date', required=True, default=fields.Date.today())
    type = fields.Selection(
        [('student', 'Student'), ('faculty', 'Faculty')],
        'Type', default='student', required=True)
    # Hide/deprecate the original student_id field
    student_id = fields.Many2one('op.student', string='OpenEducat Student', 
                                   readonly=True, copy=False)
    
    # Make wk_student_id the primary student field
    wk_student_id = fields.Many2one('student.student', string='Student',
                                     ondelete='restrict', tracking=True, index=True)
    faculty_id = fields.Many2one('op.faculty', 'Faculty',
                                 domain=[('library_card_id', '=', False)])
    active = fields.Boolean(default=True)

    _sql_constraints = [(
        'unique_library_card_number',
        'unique(number)',
        'Library card Number should be unique per card!')]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            x = self.env['ir.sequence'].next_by_code(
                'op.library.card') or '/'
            vals['number'] = x
        res = super(OpLibraryCard, self).create(vals_list)
        if res.type == 'student':
            res.student_id.library_card_id = res
        else:
            res.faculty_id.library_card_id = res
        return res

    @api.onchange('type')
    def onchange_type(self):
        self.student_id = False
        self.faculty_id = False
        self.partner_id = False

    @api.onchange('student_id', 'faculty_id')
    def onchange_student_faculty(self):
        if self.student_id:
            self.partner_id = self.student_id.partner_id
        if not self.student_id and self.faculty_id:
            self.partner_id = self.faculty_id.partner_id

    #New Add field
    @api.depends('type', 'wk_student_id', 'faculty_id')
    def _compute_partner_id(self):
        """Override to use wk_student_id instead of student_id"""
        for card in self:
            if card.type == 'student' and card.wk_student_id:
                card.partner_id = card.wk_student_id.partner_id
            elif card.type == 'faculty' and card.faculty_id:
                card.partner_id = card.faculty_id.partner_id
            else:
                card.partner_id = False
    
    @api.onchange('wk_student_id')
    def _onchange_wk_student_id(self):
        """Auto-fill partner when student is selected"""
        if self.wk_student_id and self.type == 'student':
            self.partner_id = self.wk_student_id.partner_id
    
    def unlink(self):
        """Prevent deletion if there are active book movements"""
        for card in self:
            active_movements = self.env['op.media.movement'].search([
                ('library_card_id', '=', card.id),
                ('state', '!=', 'return_done')
            ])
            if active_movements:
                raise UserError(_(
                    'Cannot delete library card %s because it has %d active book movement(s). '
                    'Please return all books first.'
                ) % (card.number, len(active_movements)))
        return super().unlink()

    ##End Add Field

