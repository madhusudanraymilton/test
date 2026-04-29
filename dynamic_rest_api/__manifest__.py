# -*- coding: utf-8 -*-
{
    'name': 'Dynamic REST API Builder',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Build and manage dynamic REST API endpoints without server restart',
    'description': """
Dynamic REST API Builder
========================
Allows non-technical users to:
- Select any installed Odoo model and expose it via REST
- Choose which fields to expose per endpoint
- Add custom fields to models dynamically (no code changes needed)
- Auto-generate fully-routed REST endpoints (GET/POST/PUT/DELETE)
- Manage API keys with SHA-256 hashing
- Log every request with timing metrics
- All endpoints register/unregister at runtime — zero restarts required
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail', 'base_setup'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizards/api_key_reveal_wizard_views.xml',
        'views/dynamic_api_endpoint_views.xml',
        'views/dynamic_api_key_views.xml',
        'views/dynamic_api_log_views.xml',
        'views/menu.xml',
        'data/cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # # SCSS first
            # 'dynamic_rest_api/static/src/components/EndpointBuilder/EndpointBuilder.scss',
            # 'dynamic_rest_api/static/src/components/FieldSelector/FieldSelector.scss',
            # 'dynamic_rest_api/static/src/components/AddFieldDialog/AddFieldDialog.scss',
            # 'dynamic_rest_api/static/src/components/EndpointPreview/EndpointPreview.scss',
            # # JS registry helper
            # 'dynamic_rest_api/static/src/js/dynamic_api_registry.js',
            # # OWL components (JS + XML together)
            # 'dynamic_rest_api/static/src/components/FieldSelector/FieldSelector.xml',
            # 'dynamic_rest_api/static/src/components/FieldSelector/FieldSelector.js',
            # 'dynamic_rest_api/static/src/components/AddFieldDialog/AddFieldDialog.xml',
            # 'dynamic_rest_api/static/src/components/AddFieldDialog/AddFieldDialog.js',
            # 'dynamic_rest_api/static/src/components/EndpointPreview/EndpointPreview.xml',
            # 'dynamic_rest_api/static/src/components/EndpointPreview/EndpointPreview.js',
            # 'dynamic_rest_api/static/src/components/EndpointBuilder/EndpointBuilder.xml',
            # 'dynamic_rest_api/static/src/components/EndpointBuilder/EndpointBuilder.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}