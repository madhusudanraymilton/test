# -*- coding: utf-8 -*-
from odoo import models, fields, api

class Book_Category(models.Model):
    '''
    class category content name of category books
    '''
    _name = 'books.category'
    _description = 'books category'

    name = fields.Char(string="Category")



