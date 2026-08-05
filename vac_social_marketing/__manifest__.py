{
    'name': 'VAC Social Marketing',
    'version': '18.0.1.1.9',
    'category': 'Marketing',
    'summary': 'Social Marketing Event Management',
    'description': """
        VAC Social Marketing Module
        ============================
        - Event Management with Stages
        - Lead Management
        - Event Templates
        - Configurable Stages and Status
    """,
    'author': 'Ayesha Chowdhuury',
    'depends': ['base', 'web', 'mail', 'website', 'crm'],

    'data': [
        'security/ir.model.access.csv',
        'data/vac_sponsor_data.xml',
        'data/vac_event_stage_data.xml',
        'data/vac_event_lead_stage_data.xml',
        'data/vac_event_lead_status_data.xml',
        'data/vac_event_cron.xml',
        # 'data/mail_template_event_registration.xml',

        # Configuration Views (define actions)
        'views/vac_event_config_views.xml',
        'views/vac_event_lead_config_views.xml',   # includes Social Lead Stages views
        'views/vac_mail_template_config_views.xml',

        # Social Views (must be before menu)
        'views/vac_social_views.xml',
        'views/vac_social_invite_wizard_views.xml',
        'views/vac_social_templates.xml',

        # Main Views
        'views/vac_event_views.xml',
        'views/vac_event_lead_views.xml',

        # Wizard
        'wizard/event_invite_wizard_views.xml',
        'wizard/vac_preview_wizard_views.xml',

        # Menu (load LAST)
        'views/menu_views.xml',
        'views/vac_event_lead_generation_wizard_views.xml',
        'views/vac_lead_inherit.xml',
        'views/temp_views.xml',
        'views/tem1_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vac_social_marketing/static/src/css/vac_event.css',
            'vac_social_marketing/static/src/js/copy_link_action.js',
            'vac_social_marketing/static/src/js/copy_qr_action.js',
            'vac_social_marketing/static/src/js/lead_stage_buttons.js',
            'vac_social_marketing/static/src/js/no_search_more_many2one.js',
            'vac_social_marketing/static/src/js/vac_auto_stage_poll.js',
            'vac_social_marketing/static/src/xml/vac_lead_stage_buttons.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    # 'post_init_hook': 'post_init_hook',
    # 'post_migrate_hook': 'post_migrate_hook',
}
