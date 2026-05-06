{
    'name': 'Zencore CLM',
    'version': '19.0.0.1.0',
    'summary': 'Credit Limit Management with Role-Based Access',
    'description': """
        Zencore CLM Module
        - Role-based access control
        - Sales, Finance, Warehouse, CCM, TDO workflows
    """,
    'author': 'Zencore',
    'website': 'https://yourcompany.com',
    'category': 'MSA',  # Custom category
    'depends': ['base', 'sale', 'contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_partner_extended_views.xml',
        'views/sale_order_extended_views.xml',
       
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
