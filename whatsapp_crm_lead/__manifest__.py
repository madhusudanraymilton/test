{
    'name': 'WhatsApp CRM Lead Auto-Creation',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Automatically create CRM leads from incoming WhatsApp messages',
    'description': """
        This module extends Odoo 19 Enterprise WhatsApp integration to:
        - Listen to incoming WhatsApp messages via webhook
        - Automatically create CRM leads from new conversations
        - Link WhatsApp messages to leads
        - Track WhatsApp communication history in CRM
    """,
    'author': 'Your Company',
    'website': 'https://yourcompany.com',
    'license': 'OEEL-1',  # Enterprise license
    'depends': [
        'whatsapp',  # Enterprise module
        'crm',
        'phone_validation',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/res_config_settings_views.xml',
        #'data/whatsapp_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}