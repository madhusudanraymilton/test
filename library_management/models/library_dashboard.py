# -*- coding: utf-8 -*-

from odoo import api, fields, models


class LibraryDashboard(models.Model):
    _name = 'library.dashboard'
    _description = 'Library Dashboard'

    name = fields.Char(string='Dashboard', default='Library Dashboard')

    @api.model
    def get_dashboard_data(self):
        """Get all dashboard statistics"""

        # Books Statistics
        total_books = self.env['library.book'].search_count([])
        available_books = self.env['library.book'].search_count([('available_copies', '>', 0)])
        borrowed_books = self.env['library.book'].search_count([('state', '=', 'borrowed')])
        maintenance_books = self.env['library.book'].search_count([('state', '=', 'maintenance')])

        # Members Statistics
        total_members = self.env['library.member'].search_count([])
        student_members = self.env['library.member'].search_count([('membership_type', '=', 'student')])
        teacher_members = self.env['library.member'].search_count([('membership_type', '=', 'teacher')])
        public_members = self.env['library.member'].search_count([('membership_type', '=', 'public')])

        # Borrowing Statistics
        active_borrowings = self.env['library.borrowing'].search_count([('status', '=', 'borrowed')])
        overdue_borrowings = self.env['library.borrowing'].search_count([('status', '=', 'overdue')])
        returned_borrowings = self.env['library.borrowing'].search_count([('status', '=', 'returned')])
        total_borrowings = self.env['library.borrowing'].search_count([])

        # Fine Statistics
        unpaid_fines = self.env['library.fine'].search_count([('payment_status', '=', 'unpaid')])
        unpaid_fine_amount = sum(
            self.env['library.fine'].search([('payment_status', '=', 'unpaid')]).mapped('fine_amount'))
        paid_fine_amount = sum(self.env['library.fine'].search([('payment_status', '=', 'paid')]).mapped('fine_amount'))

        # Top Borrowed Books
        borrowing_data = self.env['library.borrowing'].read_group(
            [('status', 'in', ['borrowed', 'returned'])],
            ['book_id'],
            ['book_id'],
            limit=5,
            orderby='book_id_count desc'
        )

        top_books = []
        for data in borrowing_data:
            if data.get('book_id'):
                book = self.env['library.book'].browse(data['book_id'][0])
                top_books.append({
                    'name': book.title,
                    'count': data['book_id_count']
                })

        # Recent Borrowings
        recent_borrowings = self.env['library.borrowing'].search(
            [],
            order='borrow_date desc',
            limit=5
        )

        recent_borrowings_data = []
        for borrowing in recent_borrowings:
            recent_borrowings_data.append({
                'id': borrowing.id,
                'name': borrowing.name,
                'member': borrowing.member_id.name,
                'book': borrowing.book_id.title,
                'borrow_date': borrowing.borrow_date.strftime('%Y-%m-%d') if borrowing.borrow_date else '',
                'due_date': borrowing.due_date.strftime('%Y-%m-%d') if borrowing.due_date else '',
                'status': borrowing.status,
            })

        # Books by Category
        category_data = self.env['library.book'].read_group(
            [('category_ids', '!=', False)],
            ['category_ids'],
            ['category_ids']
        )

        books_by_category = []
        for data in category_data[:5]:  # Top 5 categories
            if data.get('category_ids'):
                category = self.env['library.category'].browse(data['category_ids'][0])
                books_by_category.append({
                    'name': category.name,
                    'count': data['category_ids_count']
                })

        return {
            'books': {
                'total': total_books,
                'available': available_books,
                'borrowed': borrowed_books,
                'maintenance': maintenance_books,
            },
            'members': {
                'total': total_members,
                'student': student_members,
                'teacher': teacher_members,
                'public': public_members,
            },
            'borrowings': {
                'active': active_borrowings,
                'overdue': overdue_borrowings,
                'returned': returned_borrowings,
                'total': total_borrowings,
            },
            'fines': {
                'unpaid_count': unpaid_fines,
                'unpaid_amount': unpaid_fine_amount,
                'paid_amount': paid_fine_amount,
            },
            'top_books': top_books,
            'recent_borrowings': recent_borrowings_data,
            'books_by_category': books_by_category,
        }