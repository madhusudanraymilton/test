from odoo import http
from odoo.http import request
import logging
import json
import hmac
import hashlib

_logger = logging.getLogger(__name__)


class WhatsAppWebhookController(http.Controller):
    
    @http.route('/whatsapp/webhook/verify', type='http', auth='none', methods=['GET'], csrf=False)
    def whatsapp_webhook_verify(self, **kwargs):
        """
        Webhook verification endpoint for Meta WhatsApp.
        Meta sends GET request with:
        - hub.mode: 'subscribe'
        - hub.challenge: random string
        - hub.verify_token: your verification token
        """
        mode = kwargs.get('hub.mode')
        token = kwargs.get('hub.verify_token')
        challenge = kwargs.get('hub.challenge')
        
        _logger.info(f'WhatsApp webhook verification request - mode: {mode}, token provided: {bool(token)}')
        
        # Get verification token from settings
        verify_token = request.env['ir.config_parameter'].sudo().get_param(
            'whatsapp.webhook_verify_token', 
            default='your_verify_token_here'
        )
        
        if mode == 'subscribe' and token == verify_token:
            _logger.info('WhatsApp webhook verified successfully')
            return challenge
        else:
            _logger.warning(f'WhatsApp webhook verification failed - expected token: {verify_token[:5]}...')
            return http.Response('Forbidden', status=403)

    @http.route('/whatsapp/webhook/incoming', type='http', auth='none', methods=['POST'], csrf=False)
    def whatsapp_webhook_incoming(self, **kwargs):
        """
        Handle incoming WhatsApp messages from Meta webhook.
        
        Expected payload structure (from Meta):
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15551877798",
                            "phone_number_id": "911549885382061"
                        },
                        "contacts": [{
                            "profile": {"name": "Madhusudan Ray"},
                            "wa_id": "8801866754369"
                        }],
                        "messages": [{
                            "from": "8801866754369",
                            "id": "wamid.xxx",
                            "timestamp": "1769581948",
                            "text": {"body": "Hello"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        """
        try:
            # Get raw request data
            payload_str = request.httprequest.data.decode('utf-8')
            payload = json.loads(payload_str)
            
            _logger.info(f'Received WhatsApp webhook payload: {json.dumps(payload, indent=2)}')
            
            # Verify webhook signature (recommended for production)
            signature = request.httprequest.headers.get('X-Hub-Signature-256', '')
            if signature and not self._verify_webhook_signature(payload_str, signature):
                _logger.warning('WhatsApp webhook signature verification failed')
                return http.Response(
                    json.dumps({'status': 'error', 'message': 'Invalid signature'}),
                    status=403,
                    mimetype='application/json'
                )
            
            # Check if it's a WhatsApp Business Account message
            if payload.get('object') != 'whatsapp_business_account':
                _logger.warning(f'Unexpected webhook object type: {payload.get("object")}')
                return http.Response(
                    json.dumps({'status': 'ok'}),
                    status=200,
                    mimetype='application/json'
                )
            
            # Process entries
            entries = payload.get('entry', [])
            
            for entry in entries:
                business_account_id = entry.get('id')
                changes = entry.get('changes', [])
                
                for change in changes:
                    field = change.get('field')
                    
                    # Only process 'messages' field
                    if field != 'messages':
                        continue
                    
                    value = change.get('value', {})
                    metadata = value.get('metadata', {})
                    contacts = value.get('contacts', [])
                    messages = value.get('messages', [])
                    
                    # Process each message
                    for message in messages:
                        self._process_single_message(
                            message=message,
                            contacts=contacts,
                            metadata=metadata,
                            business_account_id=business_account_id
                        )
            
            # Return 200 OK to Meta
            return http.Response(
                json.dumps({'status': 'ok'}),
                status=200,
                mimetype='application/json'
            )
            
        except json.JSONDecodeError as e:
            _logger.error(f'Invalid JSON in WhatsApp webhook: {str(e)}')
            return http.Response(
                json.dumps({'status': 'error', 'message': 'Invalid JSON'}),
                status=400,
                mimetype='application/json'
            )
        except Exception as e:
            _logger.error(f'Error processing WhatsApp webhook: {str(e)}', exc_info=True)
            return http.Response(
                json.dumps({'status': 'error', 'message': str(e)}),
                status=500,
                mimetype='application/json'
            )

    def _verify_webhook_signature(self, payload_str, signature):
        """
        Verify Meta webhook signature using app secret.
        Signature format: sha256=<signature>
        """
        try:
            app_secret = request.env['ir.config_parameter'].sudo().get_param(
                'whatsapp.app_secret',
                default=''
            )
            
            if not app_secret:
                _logger.warning('WhatsApp app secret not configured, skipping signature verification')
                return True
            
            # Remove 'sha256=' prefix
            expected_signature = signature.replace('sha256=', '')
            
            # Calculate signature
            calculated_signature = hmac.new(
                app_secret.encode('utf-8'),
                payload_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(calculated_signature, expected_signature)
            
        except Exception as e:
            _logger.error(f'Error verifying webhook signature: {str(e)}')
            return False

    def _process_single_message(self, message, contacts, metadata, business_account_id):
        """
        Process a single WhatsApp message and create/update lead.
        
        Args:
            message: Message object from webhook
            contacts: Contact info from webhook
            metadata: Metadata from webhook (phone number info)
            business_account_id: WhatsApp Business Account ID
        """
        try:
            # Extract message data
            message_id = message.get('id')
            from_number = message.get('from')
            timestamp = message.get('timestamp')
            message_type = message.get('type')
            
            # Get contact name
            contact_name = ''
            wa_id = from_number
            
            for contact in contacts:
                if contact.get('wa_id') == from_number:
                    contact_name = contact.get('profile', {}).get('name', '')
                    break
            
            # Extract message content based on type
            message_content = self._extract_message_content(message, message_type)
            
            if not message_content:
                _logger.warning(f'Could not extract content from message type: {message_type}')
                return
            
            # Format phone number with country code
            phone_number = f'+{from_number}' if not from_number.startswith('+') else from_number
            
            # Get phone number receiving the message
            display_phone_number = metadata.get('display_phone_number', '')
            phone_number_id = metadata.get('phone_number_id', '')
            
            _logger.info(f'Processing WhatsApp message from {phone_number} ({contact_name}): {message_content[:50]}...')
            
            # Create message data structure
            message_data = {
                'message_id': message_id,
                'from': phone_number,
                'wa_id': wa_id,
                'timestamp': timestamp,
                'type': message_type,
                'content': message_content,
                'contact_name': contact_name,
                'display_phone_number': display_phone_number,
                'phone_number_id': phone_number_id,
                'business_account_id': business_account_id,
            }
            
            # Process in Odoo with sudo to avoid permission issues
            request.env['whatsapp.message'].sudo().with_context(
                tracking_disable=True
            )._process_incoming_message(message_data)
            
            _logger.info(f'Successfully processed WhatsApp message {message_id}')
            
        except Exception as e:
            _logger.error(f'Error processing single WhatsApp message: {str(e)}', exc_info=True)

    def _extract_message_content(self, message, message_type):
        """Extract content from different message types."""
        
        if message_type == 'text':
            return message.get('text', {}).get('body', '')
        
        elif message_type == 'image':
            caption = message.get('image', {}).get('caption', '')
            image_id = message.get('image', {}).get('id', '')
            return f'[Image: {image_id}] {caption}'.strip()
        
        elif message_type == 'document':
            filename = message.get('document', {}).get('filename', 'document')
            caption = message.get('document', {}).get('caption', '')
            return f'[Document: {filename}] {caption}'.strip()
        
        elif message_type == 'audio':
            audio_id = message.get('audio', {}).get('id', '')
            return f'[Audio message: {audio_id}]'
        
        elif message_type == 'video':
            caption = message.get('video', {}).get('caption', '')
            video_id = message.get('video', {}).get('id', '')
            return f'[Video: {video_id}] {caption}'.strip()
        
        elif message_type == 'location':
            location = message.get('location', {})
            latitude = location.get('latitude', '')
            longitude = location.get('longitude', '')
            name = location.get('name', '')
            address = location.get('address', '')
            return f'[Location: {name or address} ({latitude}, {longitude})]'
        
        elif message_type == 'contacts':
            contacts = message.get('contacts', [])
            if contacts:
                contact = contacts[0]
                name = contact.get('name', {}).get('formatted_name', '')
                return f'[Contact: {name}]'
        
        elif message_type == 'sticker':
            sticker_id = message.get('sticker', {}).get('id', '')
            return f'[Sticker: {sticker_id}]'
        
        else:
            return f'[Unsupported message type: {message_type}]'