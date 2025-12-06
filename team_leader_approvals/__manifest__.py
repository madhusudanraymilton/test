{
    'name': 'Team Leader Approvals',
    'version': '1.0',
    'summary': 'Team Leader approval system for portal users',
    'category': 'Human Resources',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr', 'hr_holidays', 'portal', 'mail'],
    'data': [
        'security/security_rules.xml',
        'security/ir.model.access.csv',
        'data/portal_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_views.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'team_leader_approvals/static/src/css/custom.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}