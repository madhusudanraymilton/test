# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LibraryConfigSettings(models.TransientModel):
    _name = 'library.config.settings'
    _description = 'Library Configuration Settings'
    _inherit = 'res.config.settings'

    # Fine settings
    fine_per_day = fields.Float(
        string='Fine Amount Per Day (₹)',
        default=5.0,
        config_parameter='library.fine_per_day'
    )
    max_borrowing_days = fields.Integer(
        string='Maximum Borrowing Days',
        default=14,
        config_parameter='library.max_borrowing_days'
    )

    # Borrowing limits
    student_max_books = fields.Integer(
        string='Student Max Books',
        default=3,
        config_parameter='library.student_max_books'
    )
    teacher_max_books = fields.Integer(
        string='Teacher Max Books',
        default=5,
        config_parameter='library.teacher_max_books'
    )
    public_max_books = fields.Integer(
        string='Public Max Books',
        default=2,
        config_parameter='library.public_max_books'
    )

    # Notification settings
    send_borrow_confirmation = fields.Boolean(
        string='Send Borrow Confirmation',
        default=True,
        config_parameter='library.send_borrow_confirmation'
    )
    send_return_confirmation = fields.Boolean(
        string='Send Return Confirmation',
        default=True,
        config_parameter='library.send_return_confirmation'
    )
    send_fine_notification = fields.Boolean(
        string='Send Fine Notification',
        default=True,
        config_parameter='library.send_fine_notification'
    )

    # Email settings
    library_email = fields.Char(
        string='Library Email',
        config_parameter='library.library_email'
    )
    overdue_reminder_days = fields.Integer(
        string='Overdue Reminder Days',
        default=2,
        config_parameter='library.overdue_reminder_days'
    )

    # Display settings
    display_qr_codes = fields.Boolean(
        string='Display QR Codes',
        default=True,
        config_parameter='library.display_qr_codes'
    )
    display_book_covers = fields.Boolean(
        string='Display Book Covers',
        default=True,
        config_parameter='library.display_book_covers'
    )

    @api.constrains('fine_per_day')
    def _check_fine_per_day(self):
        """Validate fine per day is positive"""
        for setting in self:
            if setting.fine_per_day < 0:
                raise ValidationError(_('Fine amount per day cannot be negative.'))

    @api.constrains('max_borrowing_days')
    def _check_max_borrowing_days(self):
        """Validate max borrowing days"""
        for setting in self:
            if setting.max_borrowing_days < 1:
                raise ValidationError(_('Maximum borrowing days must be at least 1.'))

    @api.constrains('student_max_books', 'teacher_max_books', 'public_max_books')
    def _check_max_books(self):
        """Validate max books per member type"""
        for setting in self:
            if any([setting.student_max_books < 1,
                    setting.teacher_max_books < 1,
                    setting.public_max_books < 1]):
                raise ValidationError(_('Maximum books per member must be at least 1.'))

    @api.constrains('overdue_reminder_days')
    def _check_overdue_reminder_days(self):
        """Validate overdue reminder days"""
        for setting in self:
            if setting.overdue_reminder_days < 0:
                raise ValidationError(_('Overdue reminder days cannot be negative.'))