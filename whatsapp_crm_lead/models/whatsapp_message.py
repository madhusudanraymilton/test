from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class WhatsAppMessage(models.Model):
    _inherit = 'whatsapp.message'

    lead_id = fields.Many2one(
        'crm.lead',
        string='Related Lead',
        ondelete='set null',
        index=True,
        help='CRM Lead created or linked from this WhatsApp message'
    )
    
    whatsapp_message_id = fields.Char(
        string='WhatsApp Message ID',
        index=True,
        help='Unique message ID from WhatsApp'
    )
    
    wa_id = fields.Char(
        string='WhatsApp ID',
        help='WhatsApp ID of the sender'
    )

    @api.model
    def _process_incoming_message(self, message_data):
        """
        Process incoming WhatsApp message and create lead if needed.
        
        message_data structure:
        {
            'message_id': 'wamid.xxx',
            'from': '+8801866754369',
            'wa_id': '8801866754369',
            'timestamp': '1769581948',
            'type': 'text',
            'content': 'Hello',
            'contact_name': 'Madhusudan Ray',
            'display_phone_number': '15551877798',
            'phone_number_id': '911549885382061',
            'business_account_id': '811451038674779',
        }
        """
        try:
            # Check if message already processed (avoid duplicates)
            message_id = message_data.get('message_id')
            if message_id:
                existing_message = self.search([
                    ('whatsapp_message_id', '=', message_id)
                ], limit=1)
                
                if existing_message:
                    _logger.info(f'WhatsApp message {message_id} already processed, skipping')
                    return existing_message
            
            # Get configuration
            auto_create_lead = self.env['ir.config_parameter'].sudo().get_param(
                'whatsapp_crm_lead.auto_create_lead', 
                default='True'
            )
            auto_create_lead = auto_create_lead in ('True', 'true', '1')
            
            # Extract message details
            phone_number = message_data.get('from', '')
            message_content = message_data.get('content', '')
            contact_name = message_data.get('contact_name', '')
            message_type = message_data.get('type', 'text')
            timestamp = message_data.get('timestamp', '')
            
            # Convert timestamp to datetime
            message_datetime = datetime.fromtimestamp(int(timestamp)) if timestamp else fields.Datetime.now()
            
            _logger.info(f'Processing WhatsApp message from {phone_number}: {message_content[:100]}')
            
            # Find or create partner
            partner = self._find_or_create_partner(phone_number, contact_name)
            
            # Create WhatsApp message record
            whatsapp_message = self.create({
                'whatsapp_message_id': message_id,
                'mobile_number': phone_number,
                'wa_id': message_data.get('wa_id'),
                'body': message_content,
                'state': 'received',
                'create_date': message_datetime,
            })
            
            if not auto_create_lead:
                _logger.info('Auto-create lead is disabled, message logged only')
                return whatsapp_message
            
            # Check for existing open lead
            update_existing = self.env['ir.config_parameter'].sudo().get_param(
                'whatsapp_crm_lead.update_existing_lead',
                default='True'
            )
            update_existing = update_existing in ('True', 'true', '1')
            
            existing_lead = None
            if update_existing:
                existing_lead = self.env['crm.lead'].search([
                    ('partner_id', '=', partner.id),
                    ('type', '=', 'lead'),
                    '|',
                    ('stage_id.is_won', '=', False),
                    ('stage_id', '=', False),
                    ('active', '=', True),
                ], limit=1, order='create_date desc')
            
            if existing_lead:
                # Update existing lead
                _logger.info(f'Updating existing lead {existing_lead.id} with WhatsApp message')
                
                existing_lead.message_post(
                    body=f"""
                        <div class="o_mail_notification">
                            <p><strong>📱 New WhatsApp Message</strong></p>
                            <p><strong>From:</strong> {contact_name or phone_number}</p>
                            <p><strong>Time:</strong> {message_datetime}</p>
                            <p><strong>Message:</strong></p>
                            <p>{message_content}</p>
                        </div>
                    """,
                    subject='New WhatsApp Message',
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
                
                whatsapp_message.write({'lead_id': existing_lead.id})
                
            else:
                # Create new lead
                lead = self._create_lead_from_whatsapp(
                    partner=partner,
                    message_content=message_content,
                    phone_number=phone_number,
                    contact_name=contact_name,
                    message_datetime=message_datetime,
                )
                
                _logger.info(f'Created new lead {lead.id} from WhatsApp message')
                whatsapp_message.write({'lead_id': lead.id})
            
            return whatsapp_message
            
        except Exception as e:
            _logger.error(f'Error processing incoming WhatsApp message: {str(e)}', exc_info=True)
            raise

    def _find_or_create_partner(self, phone_number, contact_name):
        """Find existing partner by phone or create new one."""
        # Clean phone number for search
        clean_phone = phone_number.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Search for existing partner by phone
        partner = self.env['res.partner'].search([
            '|', '|',
            ('phone', 'ilike', clean_phone),
            ('mobile', 'ilike', clean_phone),
            ('mobile', '=', phone_number),
        ], limit=1)
        
        if not partner:
            # Create new partner
            partner_vals = {
                'name': contact_name or f'WhatsApp Contact {phone_number}',
                'mobile': phone_number,
                'phone': phone_number,
                'type': 'contact',
                'company_type': 'person',
            }
            
            partner = self.env['res.partner'].create(partner_vals)
            _logger.info(f'Created new partner {partner.id} ({partner.name}) for WhatsApp contact {phone_number}')
        else:
            # Update partner name if we have a better name
            if contact_name and (not partner.name or partner.name.startswith('WhatsApp Contact')):
                partner.write({'name': contact_name})
        
        return partner

    def _create_lead_from_whatsapp(self, partner, message_content, phone_number, contact_name, message_datetime):
        """Create CRM lead from WhatsApp message."""
        
        # Get default sales team that uses leads
        team = self.env['crm.team'].search([
            ('use_leads', '=', True),
        ], limit=1, order='sequence')
        
        if not team:
            # Get any sales team
            team = self.env['crm.team'].search([], limit=1)
        
        # Get configuration for lead source
        lead_source_id = self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_crm_lead.default_source_id'
        )
        
        # Create lead name
        lead_name = f'WhatsApp: {contact_name or phone_number}'
        
        # Prepare lead values
        lead_vals = {
            'name': lead_name,
            'type': 'lead',
            'partner_id': partner.id,
            'contact_name': contact_name or partner.name,
            'phone': phone_number,
            'mobile': phone_number,
            'description': f'Initial WhatsApp message:\n\n{message_content}',
            'team_id': team.id if team else False,
            'user_id': team.user_id.id if team and team.user_id else False,
            'referred': f'WhatsApp - {phone_number}',
            'date_open': message_datetime,
        }
        
        # Add source if configured
        if lead_source_id:
            try:
                lead_vals['source_id'] = int(lead_source_id)
            except (ValueError, TypeError):
                pass
        
        # Create the lead
        lead = self.env['crm.lead'].create(lead_vals)
        
        # Post initial message
        lead.message_post(
            body=f"""
                <div class="o_mail_notification">
                    <p><strong>📱 Lead Created from WhatsApp</strong></p>
                    <p><strong>Contact:</strong> {contact_name or phone_number}</p>
                    <p><strong>Phone:</strong> {phone_number}</p>
                    <p><strong>Time:</strong> {message_datetime}</p>
                    <p><strong>Initial Message:</strong></p>
                    <p>{message_content}</p>
                </div>
            """,
            subject='Lead created from WhatsApp',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        _logger.info(f'Created CRM lead {lead.id} ({lead.name}) from WhatsApp message')
        
        return lead