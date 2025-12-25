# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class LibraryPublisher(models.Model):
    _name = 'library.publisher'
    _description = 'Library Publisher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        index=True
    )
    address = fields.Text(
        string='Address',
        tracking=True
    )
    email = fields.Char(
        string='Email',
        tracking=True
    )
    phone = fields.Char(
        string='Phone',
        tracking=True
    )
    website = fields.Char(
        string='Website',
        tracking=True
    )
    book_ids = fields.One2many(
        comodel_name='library.book',
        inverse_name='publisher_id',
        string='Books'
    )
    book_count = fields.Integer(
        string='Number of Books',
        compute='_compute_book_count',
        store=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.depends('book_ids')
    def _compute_book_count(self):
        """Compute the number of books by this publisher"""
        for publisher in self:
            publisher.book_count = len(publisher.book_ids)

    @api.constrains('email')
    def _check_email(self):
        """Validate email format"""
        for publisher in self:
            if publisher.email:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, publisher.email):
                    raise ValidationError(_('Please enter a valid email address.'))

    @api.constrains('website')
    def _check_website(self):
        """Validate website URL format"""
        for publisher in self:
            if publisher.website:
                url_pattern = r'^(https?://)?(www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(/.*)?$'
                if not re.match(url_pattern, publisher.website):
                    raise ValidationError(_('Please enter a valid website URL.'))

    def action_view_books(self):
        """Smart button action to view publisher's books"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Books by %s') % self.name,
            'res_model': 'library.book',
            'view_mode': 'tree,form',
            'domain': [('publisher_id', '=', self.id)],
            'context': {'default_publisher_id': self.id},
        }