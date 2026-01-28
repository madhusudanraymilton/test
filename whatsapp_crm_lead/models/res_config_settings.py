from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    whatsapp_auto_create_lead = fields.Boolean(
        string='Auto-create Leads from WhatsApp',
        config_parameter='whatsapp_crm_lead.auto_create_lead',
        default=True,
        help='Automatically create CRM leads when receiving WhatsApp messages from new contacts'
    )
    
    whatsapp_lead_source_id = fields.Many2one(
        'utm.source',
        string='Default Lead Source',
        config_parameter='whatsapp_crm_lead.default_source_id',
        help='Default source for leads created from WhatsApp'
    )
    
    whatsapp_update_existing_lead = fields.Boolean(
        string='Update Existing Leads',
        config_parameter='whatsapp_crm_lead.update_existing_lead',
        default=True,
        help='Add WhatsApp messages to existing open leads instead of creating duplicates'
    )