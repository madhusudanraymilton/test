# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api
'''
copies with the internal name _name set to 'book.copies'
 and a description _description set to 'books.copies'.
 These lines define different fields in the book.copies model:
name: A character field to hold the name of the book copy.
book_id: A many-to-one field that establishes a relationship with the books.data model. 
It represents the book associated with the copy.
state: A selection field that allows the user to choose the state of the book copy (lost, borrowed, or available).
start_date: A datetime field that holds the starting date of the book copy.
end_date: A date field that represents the end date of the book copy. 
It is computed based on the start_date and duration fields.
'''

class bookcopies(models.Model):
    _name = 'book.copies'
    _description = 'books.copies'

    name = fields.Char()
    book_id = fields.Many2one('books.data', string='Book')
    # count = fields.Integer(related="book_id.copy_count")
    state = fields.Selection([('lost', 'Lost'),
                              ('borrowed', 'Borrowed'),
                              ('available', 'Available'),
                              ], default="available", string='state', required=True,readonly=True)

    start_date = fields.Datetime(default=fields.Datetime.today)
    end_date = fields.Date(string="End Date", store=True,
                           compute='_get_end_date_', inverse='_set_end_date')
    progress = fields.Integer(string="Progress", compute='_compute_progress')
    place = fields.Char(string="Place")




    @api.depends('start_date', 'duration')
    def _get_end_date(self):
        """
            Sets the end date based on the start date and duration.

            This method calculates the end date by adding the duration (in days) to the start date.
            The calculated end date is then assigned to the 'end_date' field of the record.

            If either the start date or duration is not available, the function does nothing.

            Note: This method assumes that the 'start_date' and 'duration' fields are already populated.
            """
        for r in self:
            if not (r.start_date and r.duration):
                r.end_date = r.start_date
                continue

            duration = timedelta(days=r.duration, seconds=-1)
            r.end_date = r.start_date + duration

    def _set_end_date(self):
        for r in self:
            if not (r.start_date and r.duration):
                continue

            r.duration = (r.end_date - r.start_date).days + 1




    @api.onchange('book_id')
    def _onchange_book_id(self):
        '''
        This is a decorated function that is triggered when the book_id field value is changed.
        Inside the function, it checks if book_id has a value, and if so,
         it performs a search to count the number of copies associated with the same book.
        It then sets the name field of the current record to the concatenation of the book's name and the copy count plus one.
        '''
        if self.book_id:
            copy_count = self.search_count([('book_id', '=', self.book_id.id)])
            self.name = self.book_id.name +' # '+ str(copy_count + 1)



    @api.depends('state')
    def _compute_progress(self):
        for rec in self:
            if rec.state =='lost':
                progress = 0
            elif rec.state =='borrowed':
                progress = 50
            elif rec.state == 'available':
                progress =100
            else:
                progress = 25
            rec.progress =progress
