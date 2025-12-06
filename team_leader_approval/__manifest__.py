# -*- coding: utf-8 -*-
{
    'name': "Team Leader Approval",
    'version': '1.0',
    'summary': 'Team Leader Approval System',
    'description': """
        Team Leader Approves for the first time.
    """,
    'author': 'BdCalling It Ltd.',
    'website': 'https://bdcallingit.com',
    'category': 'portal',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'website',
        'portal',
        'hr_holidays',
        'hr',
    ],

    'data': [
        # XML, CSV files loaded at module installation
        # 'security/ir.model.access.csv',
        # 'views/my_custom_view.xml',
    ],

    'assets': {
        'web.assets_backend': [
            # 'your_module/static/src/js/my_script.js',
            # 'your_module/static/src/xml/my_template.xml',
        ],
    },
    "demo": [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
