# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LibraryAuthor(models.Model):
    _name = 'library.author'
    _description = 'Library Author'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        index=True
    )
    biography = fields.Text(
        string='Biography',
        tracking=True
    )
    date_of_birth = fields.Date(
        string='Date of Birth',
        tracking=True
    )
    nationality = fields.Char(
        string='Nationality',
        tracking=True
    )
    photo = fields.Image(
        string='Photo',
        max_width=1024,
        max_height=1024
    )
    book_ids = fields.Many2many(
        comodel_name='library.book',
        relation='library_book_author_rel',
        column1='author_id',
        column2='book_id',
        string='Books',
        compute='_compute_book_ids'
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

    def _compute_book_ids(self):
        """Compute books written by this author"""
        for author in self:
            author.book_ids = self.env['library.book'].search([
                ('author_ids', 'in', author.id)
            ])

    @api.depends('book_ids')
    def _compute_book_count(self):
        """Compute the number of books by this author"""
        for author in self:
            author.book_count = len(author.book_ids)

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        """Validate date of birth is not in the future"""
        for author in self:
            if author.date_of_birth and author.date_of_birth > fields.Date.today():
                raise ValidationError(_('Date of birth cannot be in the future.'))

    def action_view_books(self):
        """Smart button action to view author's books"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Books by %s') % self.name,
            'res_model': 'library.book',
            'view_mode': 'list,form',
            'domain': [('author_ids', 'in', self.id)],
            'context': {'default_author_ids': [(6, 0, [self.id])]},
        }