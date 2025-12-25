# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        index=True
    )
    email = fields.Char(
        string='Email',
        required=True,
        tracking=True,
        index=True
    )
    phone = fields.Char(
        string='Phone',
        tracking=True
    )
    address = fields.Text(
        string='Address',
        tracking=True
    )
    membership_date = fields.Date(
        string='Membership Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )
    membership_type = fields.Selection(
        selection=[
            ('student', 'Student'),
            ('teacher', 'Teacher'),
            ('public', 'Public'),
        ],
        string='Membership Type',
        required=True,
        default='public',
        tracking=True
    )
    photo = fields.Image(
        string='Photo',
        max_width=1024,
        max_height=1024
    )
    borrowing_ids = fields.One2many(
        comodel_name='library.borrowing',
        inverse_name='member_id',
        string='Borrowings'
    )
    active_borrowings = fields.Integer(
        string='Active Borrowings',
        compute='_compute_active_borrowings',
        store=True
    )
    total_books_borrowed = fields.Integer(
        string='Total Books Borrowed',
        compute='_compute_total_books_borrowed',
        store=True
    )
    fine_ids = fields.One2many(
        comodel_name='library.fine',
        inverse_name='member_id',
        string='Fines'
    )
    unpaid_fine_amount = fields.Float(
        string='Unpaid Fines',
        compute='_compute_unpaid_fine_amount',
        store=True
    )
    total_fine_paid = fields.Float(
        string='Total Fines Paid',
        compute='_compute_total_fine_paid',
        store=True
    )
    can_borrow = fields.Boolean(
        string='Can Borrow Books',
        compute='_compute_can_borrow',
        store=True
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Related User',
        help='Link this member to an Odoo user for portal access',
        ondelete='restrict'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    _sql_constraints = [
        ('email_unique', 'UNIQUE(email)', 'Email must be unique!'),
    ]

    @api.depends('borrowing_ids.status')
    def _compute_active_borrowings(self):
        """Compute number of active borrowings"""
        for member in self:
            member.active_borrowings = self.env['library.borrowing'].search_count([
                ('member_id', '=', member.id),
                ('status', '=', 'borrowed')
            ])

    @api.depends('borrowing_ids')
    def _compute_total_books_borrowed(self):
        """Compute total number of books borrowed"""
        for member in self:
            member.total_books_borrowed = len(member.borrowing_ids)

    @api.depends('fine_ids.payment_status', 'fine_ids.fine_amount')
    def _compute_unpaid_fine_amount(self):
        """Compute total unpaid fines"""
        for member in self:
            unpaid_fines = member.fine_ids.filtered(lambda f: f.payment_status == 'unpaid')
            member.unpaid_fine_amount = sum(unpaid_fines.mapped('fine_amount'))

    @api.depends('fine_ids.payment_status', 'fine_ids.fine_amount')
    def _compute_total_fine_paid(self):
        """Compute total paid fines"""
        for member in self:
            paid_fines = member.fine_ids.filtered(lambda f: f.payment_status == 'paid')
            member.total_fine_paid = sum(paid_fines.mapped('fine_amount'))

    @api.depends('unpaid_fine_amount', 'active')
    def _compute_can_borrow(self):
        """Check if member can borrow books"""
        for member in self:
            member.can_borrow = member.active and member.unpaid_fine_amount == 0

    @api.constrains('email')
    def _check_email(self):
        """Validate email format"""
        for member in self:
            if member.email:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, member.email):
                    raise ValidationError(_('Please enter a valid email address.'))

    @api.constrains('membership_date')
    def _check_membership_date(self):
        """Validate membership date"""
        for member in self:
            if member.membership_date and member.membership_date > fields.Date.today():
                raise ValidationError(_('Membership date cannot be in the future.'))

    def action_view_borrowings(self):
        """Smart button action to view member's borrowings"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Borrowings of %s') % self.name,
            'res_model': 'library.borrowing',
            'view_mode': 'tree,form,calendar',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_view_fines(self):
        """Smart button action to view member's fines"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fines of %s') % self.name,
            'res_model': 'library.fine',
            'view_mode': 'tree,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }