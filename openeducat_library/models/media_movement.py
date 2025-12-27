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

from datetime import timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OpMediaMovement(models.Model):
    _name = "op.media.movement"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Book Movement"
    _rec_name = "media_id"
    _order = "issued_date desc, id desc"

    # Core fields
    name = fields.Char('Movement #', readonly=True, copy=False)
    
    # IMPORTANT: This is the field you asked about
    media_id = fields.Many2one(
        'op.media',  # Links to the book/media master table
        'Book',
        required=True,
        tracking=True,
        help="Select the book to issue"
    )
    
    media_unit_id = fields.Many2one(
        'op.media.unit',
        'Book Copy',
        required=True,
        tracking=True,
        domain="[('media_id', '=', media_id), ('state', '=', 'available')]",
        help="Select specific copy of the book"
    )
    
    library_card_id = fields.Many2one(
        'op.library.card',
        'Library Card',
        required=True,
        tracking=True
    )
    
    # Integration fields - AUTO-POPULATED
    type = fields.Selection([
        ('student', 'Student'),
        ('faculty', 'Faculty')
    ], 'Type', required=True, compute='_compute_type', store=True)
    
    student_id = fields.Many2one(
        'student.student',
        'Student',
        compute='_compute_borrower',
        store=True
    )
    
    faculty_id = fields.Many2one(
        'hr.employee',
        'Faculty',
        compute='_compute_borrower',
        store=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        'Person',
        compute='_compute_borrower',
        store=True
    )
    
    current_grade_id = fields.Many2one(
        'wk.school.grade',
        related='student_id.current_grade_id',
        string='Grade',
        store=True
    )
    
    # Dates
    issued_date = fields.Date(
        'Issue Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    return_date = fields.Date(
        'Due Date',
        compute='_compute_return_date',
        store=True,
        readonly=False,
        required=True
    )
    actual_return_date = fields.Date('Returned On', tracking=True)
    
    # Status
    state = fields.Selection([
        ('issue', 'Issued'),
        ('reissue', 'Renewed'),
        ('return', 'Returned'),
        ('return_done', 'Returned (Paid)'),
        ('lost', 'Lost')
    ], 'Status', default='issue', required=True, tracking=True)
    
    # Financial
    penalty = fields.Float(
        'Penalty Amount',
        compute='_compute_penalty',
        store=True,
        tracking=True
    )
    penalty_paid = fields.Boolean('Penalty Paid', default=False)
    invoice_id = fields.Many2one('account.move', 'Invoice', readonly=True)
    
    # Computed fields
    days_overdue = fields.Integer('Days Overdue', compute='_compute_days_overdue')
    is_overdue = fields.Boolean('Overdue', compute='_compute_is_overdue')
    
    company_id = fields.Many2one(
        'res.company',
        'School',
        default=lambda self: self.env.company,
        required=True
    )
    
    active = fields.Boolean(default=True)
    notes = fields.Text('Notes')

    @api.depends('library_card_id')
    def _compute_type(self):
        """Auto-populate type from library card"""
        for movement in self:
            movement.type = movement.library_card_id.type if movement.library_card_id else 'student'

    @api.depends('library_card_id', 'library_card_id.student_id', 'library_card_id.faculty_id')
    def _compute_borrower(self):
        """Auto-populate borrower details from library card"""
        for movement in self:
            if movement.library_card_id:
                if movement.library_card_id.type == 'student':
                    movement.student_id = movement.library_card_id.student_id
                    movement.faculty_id = False
                    movement.partner_id = movement.student_id.partner_id if movement.student_id else False
                else:
                    movement.faculty_id = movement.library_card_id.faculty_id
                    movement.student_id = False
                    movement.partner_id = movement.faculty_id.user_id.partner_id if movement.faculty_id and movement.faculty_id.user_id else False
            else:
                movement.student_id = False
                movement.faculty_id = False
                movement.partner_id = False

    @api.depends('issued_date', 'library_card_id.library_card_type_id.duration')
    def _compute_return_date(self):
        """Calculate due date based on card type duration"""
        for movement in self:
            if movement.issued_date and movement.library_card_id:
                duration = movement.library_card_id.library_card_type_id.duration or 14
                movement.return_date = movement.issued_date + timedelta(days=duration)
            elif not movement.return_date:
                movement.return_date = fields.Date.today() + timedelta(days=14)

    @api.depends('state', 'return_date', 'actual_return_date')
    def _compute_days_overdue(self):
        """Calculate days overdue"""
        today = fields.Date.today()
        for movement in self:
            if movement.state == 'issue' and movement.return_date:
                if today > movement.return_date:
                    movement.days_overdue = (today - movement.return_date).days
                else:
                    movement.days_overdue = 0
            elif movement.state in ('return', 'return_done') and movement.actual_return_date and movement.return_date:
                if movement.actual_return_date > movement.return_date:
                    movement.days_overdue = (movement.actual_return_date - movement.return_date).days
                else:
                    movement.days_overdue = 0
            else:
                movement.days_overdue = 0

    @api.depends('days_overdue', 'state')
    def _compute_is_overdue(self):
        """Check if book is overdue"""
        for movement in self:
            movement.is_overdue = movement.state == 'issue' and movement.days_overdue > 0

    @api.depends('days_overdue', 'library_card_id.library_card_type_id.penalty_amt_per_day')
    def _compute_penalty(self):
        """Calculate penalty amount"""
        for movement in self:
            if movement.days_overdue > 0:
                penalty_per_day = movement.library_card_id.library_card_type_id.penalty_amt_per_day or 0.0
                movement.penalty = movement.days_overdue * penalty_per_day
            else:
                movement.penalty = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Generate movement number"""
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('op.media.movement') or '/'
        return super().create(vals_list)

    @api.constrains('library_card_id', 'media_id', 'state')
    def _check_book_limit(self):
        """Check if borrower exceeded book limit"""
        for movement in self:
            if movement.state == 'issue':
                card = movement.library_card_id
                issued_count = self.search_count([
                    ('library_card_id', '=', card.id),
                    ('state', '=', 'issue')
                ])
                max_books = card.library_card_type_id.allow_media
                if issued_count > max_books:
                    raise ValidationError(
                        _('Book limit exceeded! Maximum %s books allowed.') % max_books
                    )

    @api.constrains('issued_date', 'return_date')
    def _check_dates(self):
        """Validate dates"""
        for movement in self:
            if movement.return_date and movement.issued_date > movement.return_date:
                raise ValidationError(_('Due date cannot be before issue date!'))

    @api.onchange('media_unit_id')
    def onchange_media_unit_id(self):
        """Auto-fill media_id when unit is selected"""
        if self.media_unit_id:
            self.media_id = self.media_unit_id.media_id

    # Actions
    def action_issue_book(self):
        """Issue the book"""
        for movement in self:
            if movement.media_unit_id:
                movement.media_unit_id.state = 'issue'
            movement.state = 'issue'

    def action_return_book(self):
        """Return the book"""
        self.ensure_one()
        
        if self.state != 'issue':
            raise ValidationError(_('Only issued books can be returned!'))
        
        self.actual_return_date = fields.Date.today()
        
        if self.penalty > 0:
            self.state = 'return'
            self._create_penalty_invoice()
        else:
            self.state = 'return_done'
        
        if self.media_unit_id:
            self.media_unit_id.state = 'available'

    def action_renew_book(self):
        """Renew book loan"""
        self.ensure_one()
        
        if self.state != 'issue':
            raise ValidationError(_('Only issued books can be renewed!'))
        
        duration = self.library_card_id.library_card_type_id.duration or 14
        self.return_date = fields.Date.today() + timedelta(days=duration)
        self.state = 'reissue'

    def action_mark_lost(self):
        """Mark book as lost"""
        self.ensure_one()
        self.state = 'lost'
        if self.media_unit_id:
            self.media_unit_id.state = 'lost'

    def _create_penalty_invoice(self):
        """Create invoice for penalty"""
        self.ensure_one()
        
        if not self.penalty or self.invoice_id:
            return
        
        product = self.env.ref('openeducat_library.op_product_7', raise_if_not_found=False)
        if not product:
            raise ValidationError(_('Library penalty product not configured!'))
        
        account_id = product.property_account_income_id.id or \
                     product.categ_id.property_account_income_categ_id.id
        
        if not account_id:
            raise ValidationError(_('Income account not configured for library penalty product!'))
        
        invoice = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': _('Library Penalty - %s (%s days overdue)') % (self.media_id.name, self.days_overdue),
                'product_id': product.id,
                'quantity': 1.0,
                'price_unit': self.penalty,
                'account_id': account_id,
            })]
        })
        
        self.invoice_id = invoice.id
        return invoice

    def action_view_invoice(self):
        """View penalty invoice"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise ValidationError(_('No invoice created yet!'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Penalty Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }