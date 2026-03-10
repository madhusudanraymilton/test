# -*- coding: utf-8 -*-
{
    'name': 'BDCalling Asset Management System',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Assets',
    'summary': 'Complete lifecycle management for organizational assets',
    'description': '''
Asset Management System (AMS)
==============================
- Asset Category Configuration with depreciation setup
- Serial number-based asset registration from inventory
- Employee assignment and return tracking
- Straight-line and declining balance depreciation
- Automated journal entry posting via cron
- Full lifecycle history (append-only audit log)
- Multi-company support
- OWL Dashboard with KPIs
- PDF reports: valuation, depreciation schedule, employee-wise
    ''',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'stock',
        'account',
        'account_asset',
        'purchase',
        'hr',
    ],
    'data': [
        # Security — MUST be first
        #'security/asset_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/asset_sequence_data.xml',
        # 'data/asset_location_data.xml',
        # 'data/asset_cron_data.xml',
        # Views
        'views/account_asset_extended_views.xml',
        'views/asset_asset_views.xml',
        'views/asset_assignment_views.xml',
        'views/asset_history_views.xml',
        'views/asset_dashboard_views.xml',
        'views/product_template_extended_views.xml',
        # 'views/res_config_settings_views.xml',
        'views/wizard_register_views.xml',
        'views/wizard_unregister_views.xml',
        'views/wizard_assign_views.xml',
        'views/wizard_return_views.xml',
        'views/asset_report_views.xml',
        'views/menu_views.xml',
        # Reports
        'report/asset_valuation_report.xml',
        'report/templates/report_asset_valuation.xml',
        'report/templates/report_asset_depreciation.xml',
    ],
    'assets': {
        'web.assets_web': [
            'asset_management_bdcalling/static/src/xml/asset_dashboard.xml',
            'asset_management_bdcalling/static/src/js/asset_dashboard.js',
            'asset_management_bdcalling/static/src/css/asset_dashboard.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
