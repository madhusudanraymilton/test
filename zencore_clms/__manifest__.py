{
    'name': 'Zencore CLM',
    'version': '19.0.0.2.0',
    'summary': 'Stage-Driven Credit Limit Management System',
    'description': """
        Zencore CLM — Credit Control Engine
        =====================================
        - Stage-driven exposure tracking (PI → Bucket 1-4 → Paid)
        - Real-time computed balances per bucket
        - Automatic credit freeze on limit breach
        - Group-level freeze propagation
        - CCM → Finance Manager approval workflow for limit changes
        - Full audit trail
    """,
    'author': 'Zencore',
    'website': 'https://zencoreltd.com',
    'category': 'msa',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'stock',
        'account',
        'contacts',
        'mail',
    ],
    'data': [
        # Security — load first
        'security/security.xml',
        'security/ir.model.access.csv',
        # Sequence data
        'data/ir_sequence_data.xml',
        # Views
        'views/res_partner_extended_views.xml',
        'views/sale_order_extended_views.xml',
        'views/clm_limit_change_request_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}