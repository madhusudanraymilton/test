# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Library Borrowing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'borrow_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    member_id = fields.Many2one(
        comodel_name='library.member',
        string='Member',
        required=True,
        tracking=True,
        ondelete='restrict',
        index=True
    )
    member_email = fields.Char(
        related='member_id.email',
        string='Member Email',
        readonly=True
    )
    member_can_borrow = fields.Boolean(
        related='member_id.can_borrow',
        string='Member Can Borrow',
        readonly=True
    )
    book_id = fields.Many2one(
        comodel_name='library.book',
        string='Book',
        required=True,
        tracking=True,
        ondelete='restrict',
        index=True
    )
    book_isbn = fields.Char(
        related='book_id.isbn',
        string='ISBN',
        readonly=True
    )
    book_available_copies = fields.Integer(
        related='book_id.available_copies',
        string='Available Copies',
        readonly=True
    )
    borrow_date = fields.Date(
        string='Borrow Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        index=True
    )
    due_date = fields.Date(
        string='Due Date',
        required=True,
        tracking=True,
        index=True
    )
    return_date = fields.Date(
        string='Return Date',
        tracking=True,
        readonly=True
    )
    status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('borrowed', 'Borrowed'),
            ('returned', 'Returned'),
            ('overdue', 'Overdue'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        index=True
    )
    fine_amount = fields.Float(
        string='Fine Amount',
        compute='_compute_fine_amount',
        store=True,
        digits='Product Price'
    )
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_days_overdue',
        store=True
    )
    fine_id = fields.Many2one(
        comodel_name='library.fine',
        string='Fine Record',
        readonly=True
    )
    notes = fields.Text(
        string='Notes'
    )
    color = fields.Integer(
        string='Color Index',
        compute='_compute_color'
    )

    @api.model
    def create(self, vals):
        """Override create to generate sequence"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('library.borrowing') or _('New')
        return super().create(vals)

    @api.depends('due_date', 'return_date', 'status')
    def _compute_days_overdue(self):
        """Compute number of days overdue"""
        for borrowing in self:
            if borrowing.status == 'returned' and borrowing.return_date:
                if borrowing.return_date > borrowing.due_date:
                    borrowing.days_overdue = (borrowing.return_date - borrowing.due_date).days
                else:
                    borrowing.days_overdue = 0
            elif borrowing.status in ['borrowed', 'overdue']:
                today = fields.Date.today()
                if today > borrowing.due_date:
                    borrowing.days_overdue = (today - borrowing.due_date).days
                else:
                    borrowing.days_overdue = 0
            else:
                borrowing.days_overdue = 0

    @api.depends('days_overdue')
    def _compute_fine_amount(self):
        """Compute fine amount based on overdue days"""
        fine_per_day = self.env['ir.config_parameter'].sudo().get_param(
            'library.fine_per_day', default=5.0
        )
        for borrowing in self:
            borrowing.fine_amount = borrowing.days_overdue * float(fine_per_day)

    def _compute_color(self):
        """Compute color for kanban view"""
        for borrowing in self:
            if borrowing.status == 'overdue':
                borrowing.color = 1  # Red
            elif borrowing.status == 'borrowed':
                days_until_due = (borrowing.due_date - fields.Date.today()).days
                if days_until_due <= 2:
                    borrowing.color = 3  # Orange
                else:
                    borrowing.color = 10  # Green
            elif borrowing.status == 'returned':
                borrowing.color = 4  # Blue
            else:
                borrowing.color = 0  # Default

    @api.onchange('borrow_date')
    def _onchange_borrow_date(self):
        """Set default due date (14 days from borrow date)"""
        if self.borrow_date:
            self.due_date = self.borrow_date + timedelta(days=14)

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """Check if member can borrow"""
        if self.member_id and not self.member_id.can_borrow:
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('This member has unpaid fines and cannot borrow books.')
                }
            }

    @api.constrains('borrow_date', 'due_date', 'return_date')
    def _check_dates(self):
        """Validate dates"""
        for borrowing in self:
            if borrowing.due_date and borrowing.borrow_date > borrowing.due_date:
                raise ValidationError(_('Due date must be after borrow date.'))
            if borrowing.return_date and borrowing.return_date < borrowing.borrow_date:
                raise ValidationError(_('Return date cannot be before borrow date.'))

    def action_confirm_borrow(self):
        """Confirm borrowing and change status to borrowed"""
        for borrowing in self:
            if not borrowing.member_id.can_borrow:
                raise UserError(_('Member %s has unpaid fines and cannot borrow books.') % borrowing.member_id.name)

            if borrowing.book_id.available_copies < 1:
                raise UserError(_('Book "%s" is not available for borrowing.') % borrowing.book_id.title)

            borrowing.status = 'borrowed'

            # Send confirmation email
            template = self.env.ref('library_management.email_template_borrowing_confirmation',
                                    raise_if_not_found=False)
            if template:
                template.send_mail(borrowing.id, force_send=True)

    def action_return_book(self):
        """Return book and create fine if overdue"""
        for borrowing in self:
            if borrowing.status != 'borrowed':
                raise UserError(_('Only borrowed books can be returned.'))

            borrowing.return_date = fields.Date.today()
            borrowing.status = 'returned'

            # Create fine if overdue
            if borrowing.days_overdue > 0 and borrowing.fine_amount > 0:
                fine = self.env['library.fine'].create({
                    'borrowing_id': borrowing.id,
                    'member_id': borrowing.member_id.id,
                    'fine_amount': borrowing.fine_amount,
                    'fine_reason': _('Book returned %d days late') % borrowing.days_overdue,
                    'payment_status': 'unpaid',
                })
                borrowing.fine_id = fine.id

                # Send fine notification email
                template = self.env.ref('library_management.email_template_fine_notification', raise_if_not_found=False)
                if template:
                    template.send_mail(fine.id, force_send=True)

    @api.model
    def _cron_check_overdue_borrowings(self):
        """Scheduled action to check and update overdue borrowings"""
        today = fields.Date.today()
        overdue_borrowings = self.search([
            ('status', '=', 'borrowed'),
            ('due_date', '<', today)
        ])

        for borrowing in overdue_borrowings:
            borrowing.status = 'overdue'

            # Send overdue notification
            template = self.env.ref('library_management.email_template_overdue_notification', raise_if_not_found=False)
            if template:
                template.send_mail(borrowing.id, force_send=True)

    def action_send_reminder(self):
        """Send reminder email to member"""
        self.ensure_one()
        template = self.env.ref('library_management.email_template_overdue_notification', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Reminder email sent to %s') % self.member_id.name,
                'type': 'success',
                'sticky': False,
            }
        }