{
    'name': 'Zencore Helpdesk Conversion API',
    'version': '19.0.1.0.0',
    'category': 'Helpdesk',
    'summary': (
        'Replaces default Helpdesk chatter email flow with '
        'an external API-based messaging bridge.'
    ),
    'description': """
        This module:
        - Disables Odoo's default outbound email from helpdesk chatter threads.
        - Exposes a public REST endpoint to receive inbound messages from an
          external portal and log them as internal chatter notes.
        - Forwards replies by the assigned user to a configured external API.
        - Sends lightweight (no-thread) email notifications to both the assigned
          agent (on inbound) and the portal user (on outbound reply).
    """,
    'author': 'Zencore',
    'depends': ['helpdesk', 'mail', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}