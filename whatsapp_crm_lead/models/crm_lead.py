from odoo import models, fields, api, _



class CrmLead(models.Model):
    _inherit = 'crm.lead'

    whatsapp_message_ids = fields.One2many(
        'whatsapp.message',
        'lead_id',
        string='WhatsApp Messages',
        help='WhatsApp messages linked to this lead'
    )
    whatsapp_message_count = fields.Integer(
        string='WhatsApp Messages',
        compute='_compute_whatsapp_message_count',
        store=True
    )
    has_whatsapp = fields.Boolean(
        string='Has WhatsApp',
        compute='_compute_has_whatsapp',
        store=True,
        help='Contact has WhatsApp capability'
    )

    @api.depends('whatsapp_message_ids')
    def _compute_whatsapp_message_count(self):
        for lead in self:
            lead.whatsapp_message_count = len(lead.whatsapp_message_ids)

    @api.depends('partner_id', 'phone')
    def _compute_has_whatsapp(self):
        for lead in self:
            # Simple check - in production, you'd verify via WhatsApp API
            lead.has_whatsapp = bool(lead.phone)

    def action_send_whatsapp(self):
        """Open WhatsApp composer for this lead."""
        self.ensure_one()
        
        if not self.mobile and not self.phone:
            raise UserError(_('No phone number found for this lead.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send WhatsApp Message'),
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'crm.lead',
                'default_res_id': self.id,
                'default_mobile': self.mobile or self.phone,
                'default_partner_id': self.partner_id.id if self.partner_id else False,
            },
        }

    def action_view_whatsapp_messages(self):
        """View all WhatsApp messages for this lead."""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('WhatsApp Messages'),
            'res_model': 'whatsapp.message',
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }