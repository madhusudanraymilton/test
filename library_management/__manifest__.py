# -*- coding: utf-8 -*-
{
    'name': 'Library Management System',
    'version': '19.0.1.0.0',
    'category': 'Services',
    'summary': 'Complete Library Management System with Books, Members, Borrowings, and Fines',
    'description': """
Library Management System
=========================
This module provides a complete library management solution with:
* Book catalog management with authors, publishers, and categories
* Member registration and management
* Book borrowing and return system
* Automatic fine calculation for overdue books
* Dashboard with statistics and charts
* Email notifications for overdue books
* QR code generation for books
* Comprehensive reports
* Multi-level security access
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',

        # Wizards
        'wizards/return_book_wizard_views.xml',

        # Views
        'views/actions.xml',
        'views/author_views.xml',
        'views/publisher_views.xml',
        'views/category_views.xml',
        'views/book_views.xml',
        'views/member_views.xml',
        'views/fine_views.xml',
        'views/borrowing_views.xml',
        'views/dashboard.xml',
        'views/menu.xml',

        # Data
       # 'data/automated_actions.xml',
       # 'data/email_templates.xml',
    ],
    'demo': [
      #  'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'library_management/static/src/css/dashboard.css',
            'library_management/static/src/js/dashboard.js',
        ],
    },
    'external_dependencies': {
        'python': ['qrcode'],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}