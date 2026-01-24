{
    'name': "Sales Features",
    'version': '19.0.1.0',
    'summary': "sales Portal Operations",
    'description': """
    """,
    'author': "Anwar Hossain",
    'website': "https://bdcalling.com/",
    'depends': ['base','sale','account'],  
    'data': [
        'security/ir.model.access.csv',
        'views/platform_source_views.xml',
        'views/profile_name_views.xml',
        'views/sales_order_extended_views.xml',
        'views/account_move_extended_views.xml',
        'views/account_payment_register_extended_views.xml',
        'views/menu.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'auto_install': False,
}