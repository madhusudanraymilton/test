# -*- coding: utf-8 -*-
{
    'name': 'ZenCore Helpdesk Conversation API',
    'version': '19.0.1.0.0',
    'category': 'Helpdesk',
    'summary': (
        'Replaces Odoo Helpdesk chatter email flow with external API-based '
        'messaging for the World University of Bangladesh portal integration.'
    ),
    'description': """
ZenCore Helpdesk Conversation API
==================================

Replaces the default Odoo Helpdesk email conversation mechanism entirely.
The Odoo Chatter is used exclusively as an internal message log.
All actual Student ↔ Teacher / Customer ↔ Agent communication occurs
through the external portal, coordinated via this API bridge.

Key Capabilities
-----------------
- Section 1 — Disables Odoo chatter outbound email thread for all helpdesk tickets.
- Section 2 — Exposes a REST endpoint for the external system to push inbound messages
              into the chatter log and trigger a lightweight assigned-user notification.
- Section 3 — When the Assigned User replies via chatter, the reply is forwarded to the
              external system API with full message payload.
- Section 4 — Parent message reference and thread context are included in all API payloads
              so the external portal can maintain threaded conversation history.
- Section 5 — Sends a lightweight notification email to the portal user (Student/Customer)
              without including any message body or thread history.

Configuration
--------------
Settings → ZenCore Helpdesk API
  - External API Endpoint (URL of external messaging system)
  - Outbound API Key     (Odoo → External system authentication)
  - Inbound API Key      (External system → Odoo authentication)
    """,
    'author': 'ZenCore',
    'website': '',
    'depends': [
        'helpdesk',
        'mail',
        'base_setup',
    ],
    'data': [
        # 'data/mail_template_data.xml',
        # 'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
