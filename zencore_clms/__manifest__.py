{
    'name': 'Zencore CLMs',
    'version': '19.0.0.3.0',
    'summary': 'Stage-Driven Credit Limit Management System',
    'description': """
        Zencore CLM — Credit Control Engine
        =====================================
        v0.3.0 — Production-hardened release
        - Stage-driven exposure tracking (PI → Bucket 1-4 → Paid)
        - Real-time computed balances per bucket (read_group optimised)
        - Automatic credit freeze on limit breach
        - Group-level freeze propagation (all children blocked if any frozen)
        - CCM → Finance Manager approval workflow for limit changes
        - Full audit trail with chatter on every stage transition
        - SoD enforcement: Salesperson / Sales Manager / CCM / Warehouse / TDO / Finance
        - Reconciliation-safe payment detection hook
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
        # Security — must be first
        'security/security.xml',
        'security/ir.model.access.csv',
        # Sequences
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
