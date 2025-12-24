# -*- coding: utf-8 -*-
{
    'name': "Library Management System",
    'version': '15.0',
    'summary': """Library Management System""",
    'description': """Imagine a library where books come to you, where due dates are automatically tracked, and where you can browse and borrow books with ease.
     That's the Odoo Library App: a symphony of automation and convenience that makes it easier than ever to enjoy the magic of books.
     """,
    'category': 'Productivity',
    'author': "Neoteric Hub",
    'company': 'Neoteric Hub',
    'live_test_url': '',
    'price': 0.0,
    'currency': 'USD',
    'website': "http://neoterichub.com",
    'depends': ['base', 'website', 'board', 'mail','contacts'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/report.xml',
        'views/report_warnning.xml',
        'views/Books_data.xml',
        'views/Author.xml',
        'views/Publisher.xml',
        'views/Borrows.xml',
        'views/Book_copies.xml',
        'views/Book_Category.xml',
        'views/res_partner.xml',
        'views/configuration.xml',
        'views/dashboard.xml',
        'views/templates.xml',
        'data/scheduled.xml',
        'views/menu.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'images': ['static/description/banner.gif'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
