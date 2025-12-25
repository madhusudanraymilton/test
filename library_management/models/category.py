# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LibraryCategory(models.Model):
    _name = 'library.category'
    _description = 'Library Category'
    _inherit = ['mail.thread']
    _order = 'complete_name'
    _parent_name = 'parent_id'
    _parent_store = True

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        index=True
    )
    description = fields.Text(
        string='Description',
        tracking=True
    )
    parent_id = fields.Many2one(
        comodel_name='library.category',
        string='Parent Category',
        ondelete='cascade',
        tracking=True,
        index=True
    )
    parent_path = fields.Char(
        index=True
    )
    child_ids = fields.One2many(
        comodel_name='library.category',
        inverse_name='parent_id',
        string='Child Categories'
    )
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        store=True,
        recursive=True
    )
    book_ids = fields.Many2many(
        comodel_name='library.book',
        relation='library_book_category_rel',
        column1='category_id',
        column2='book_id',
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

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Compute the complete hierarchical name"""
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name

    @api.depends('book_ids')
    def _compute_book_count(self):
        """Compute the number of books in this category"""
        for category in self:
            category.book_count = len(category.book_ids)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """Prevent circular hierarchies"""
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive categories.'))

    def action_view_books(self):
        """Smart button action to view category's books"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Books in %s') % self.complete_name,
            'res_model': 'library.book',
            'view_mode': 'tree,form',
            'domain': [('category_ids', 'in', self.id)],
            'context': {'default_category_ids': [(6, 0, [self.id])]},
        }

    @api.model
    def name_create(self, name):
        """Create category from name with proper format"""
        return self.create({'name': name}).name_get()[0]