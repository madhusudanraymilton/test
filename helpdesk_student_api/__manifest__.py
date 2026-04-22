# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Student REST API',
    'version': '19.0.2.0.0',
    'summary': 'JWT-secured REST API for student helpdesk ticket access',
    'description': """
        Provides JWT-authenticated REST API endpoints for students:

        Authentication
        - POST /api/v1/auth/login    – obtain access + refresh tokens
        - POST /api/v1/auth/refresh  – exchange refresh token for new access token
        - POST /api/v1/auth/logout   – revoke (blacklist) the current token

        Helpdesk
        - GET  /api/v1/helpdesk/tickets              – list all tickets by student email
        - GET  /api/v1/helpdesk/tickets/<ticket_id>  – full detail for one ticket

        Requires PyJWT >= 2.0  (pip install PyJWT)
    """,
    'category': 'Helpdesk',
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'helpdesk',
        'mail',
        'portal',
        'base_setup',       # for ir.config_parameter
    ],
    'external_dependencies': {
        'python': ['jwt'],  # PyJWT package
    },
    'data': [
        'security/ir.model.access.csv',
        'data/jwt_config_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
