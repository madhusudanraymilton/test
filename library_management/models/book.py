# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
import io


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'title'

    name = fields.Char(
        string='Title',
        compute='_compute_name',
        store=True,
        index=True
    )
    title = fields.Char(
        string='Book Title',
        required=True,
        tracking=True,
        index=True
    )
    isbn = fields.Char(
        string='ISBN',
        required=True,
        tracking=True,
        index=True,
        copy=False
    )
    description = fields.Text(
        string='Description',
        tracking=True
    )
    author_ids = fields.Many2many(
        comodel_name='library.author',
        relation='library_book_author_rel',
        column1='book_id',
        column2='author_id',
        string='Authors',
        required=True,
        tracking=True
    )
    publisher_id = fields.Many2one(
        comodel_name='library.publisher',
        string='Publisher',
        tracking=True,
        ondelete='restrict'
    )
    category_ids = fields.Many2many(
        comodel_name='library.category',
        relation='library_book_category_rel',
        column1='book_id',
        column2='category_id',
        string='Categories',
        tracking=True
    )
    publication_date = fields.Date(
        string='Publication Date',
        tracking=True
    )
    total_copies = fields.Integer(
        string='Total Copies',
        required=True,
        default=1,
        tracking=True
    )
    available_copies = fields.Integer(
        string='Available Copies',
        compute='_compute_available_copies',
        store=True
    )
    cover_image = fields.Image(
        string='Cover Image',
        max_width=1024,
        max_height=1024
    )
    price = fields.Float(
        string='Price',
        tracking=True,
        digits='Product Price'
    )
    state = fields.Selection(
        selection=[
            ('available', 'Available'),
            ('borrowed', 'Borrowed'),
            ('maintenance', 'Under Maintenance'),
        ],
        string='Status',
        default='available',
        required=True,
        tracking=True
    )
    borrowing_ids = fields.One2many(
        comodel_name='library.borrowing',
        inverse_name='book_id',
        string='Borrowings'
    )
    active_borrowing_count = fields.Integer(
        string='Active Borrowings',
        compute='_compute_active_borrowing_count',
        store=True
    )
    total_borrowed_count = fields.Integer(
        string='Times Borrowed',
        compute='_compute_total_borrowed_count',
        store=True
    )
    qr_code = fields.Binary(
        string='QR Code',
        compute='_compute_qr_code',
        store=False
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    _sql_constraints = [
        ('isbn_unique', 'UNIQUE(isbn)', 'ISBN must be unique!'),
    ]

    @api.depends('title')
    def _compute_name(self):
        """Compute name field for search and display"""
        for book in self:
            book.name = book.title

    @api.depends('total_copies', 'borrowing_ids.status')
    def _compute_available_copies(self):
        """Compute available copies based on active borrowings"""
        for book in self:
            borrowed = self.env['library.borrowing'].search_count([
                ('book_id', '=', book.id),
                ('status', '=', 'borrowed')
            ])
            book.available_copies = book.total_copies - borrowed

    @api.depends('borrowing_ids.status')
    def _compute_active_borrowing_count(self):
        """Compute number of active borrowings"""
        for book in self:
            book.active_borrowing_count = self.env['library.borrowing'].search_count([
                ('book_id', '=', book.id),
                ('status', '=', 'borrowed')
            ])

    @api.depends('borrowing_ids')
    def _compute_total_borrowed_count(self):
        """Compute total times book was borrowed"""
        for book in self:
            book.total_borrowed_count = len(book.borrowing_ids)

    def _compute_qr_code(self):
        """Generate QR code for book ISBN"""
        for book in self:
            if book.isbn:
                try:
                    import qrcode
                    qr = qrcode.QRCode(version=1, box_size=10, border=5)
                    qr.add_data(book.isbn)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    book.qr_code = base64.b64encode(buffer.getvalue())
                except ImportError:
                    book.qr_code = False
            else:
                book.qr_code = False

    @api.constrains('isbn')
    def _check_isbn(self):
        """Validate ISBN format"""
        for book in self:
            if book.isbn:
                isbn = book.isbn.replace('-', '').replace(' ', '')
                if not (len(isbn) in [10, 13] and isbn.isdigit()):
                    raise ValidationError(_('ISBN must be 10 or 13 digits.'))

    @api.constrains('total_copies')
    def _check_total_copies(self):
        """Validate total copies is positive"""
        for book in self:
            if book.total_copies < 1:
                raise ValidationError(_('Total copies must be at least 1.'))

    @api.constrains('price')
    def _check_price(self):
        """Validate price is non-negative"""
        for book in self:
            if book.price < 0:
                raise ValidationError(_('Price cannot be negative.'))

    def action_view_borrowings(self):
        """Smart button action to view book's borrowings"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Borrowings of %s') % self.title,
            'res_model': 'library.borrowing',
            'view_mode': 'tree,form,calendar',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id},
        }

    def action_set_available(self):
        """Set book status to available"""
        self.ensure_one()
        self.state = 'available'

    def action_set_maintenance(self):
        """Set book status to maintenance"""
        self.ensure_one()
        if self.available_copies < self.total_copies:
            raise ValidationError(_('Cannot set to maintenance while there are active borrowings.'))
        self.state = 'maintenance'