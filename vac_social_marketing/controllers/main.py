# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import base64

_logger = logging.getLogger(__name__)


class VacEventController(http.Controller):
    """
    Controller for VAC Event public pages
    Routes:
    - /event or /events - Event listing page (all published events)
    - /event/invite/<id> - Event registration page
    - /event/register/submit - Handle form submission
    - /event/register/success - Success confirmation page
    - /event/badge/<id> - Serve badge background image
    """
    
    @http.route(['/event', '/events'], type='http', auth='public', website=True)
    def event_listing(self, **kwargs):
        """
        Display all published events in a grid layout
        
        Returns:
            Rendered template with list of published events
        """
        # Get all published events ordered by date
        events = request.env['vac.event'].sudo().search([
            ('published', '=', True),
            ('active', '=', True)
        ], order='date asc')
        
        values = {
            'events': events,
        }
        
        _logger.info(f"Event listing page accessed - Found {len(events)} published events")
        
        # Use basic layout template (works without website module)
        return request.render('vac_social_marketing.event_listing_page', values)
    
    
    @http.route('/event/invite/<int:event_id>', type='http', auth='public', website=True)
    def event_registration_page(self, event_id, **kwargs):
        """
        Display event registration page for a specific event
        
        Args:
            event_id: ID of the event
            
        Returns:
            Rendered template with event details
        """
        event = request.env['vac.event'].sudo().browse(event_id)
        
        # Check if event exists and is published
        if not event.exists() or not event.published:
            _logger.warning(f"Event {event_id} not found or not published")
            return request.render('vac_social_marketing.event_not_found')
        
        # Prepare badge background URL if exists
        badge_bg_url = None
        if event.badge_background:
            badge_bg_url = f'/event/badge/{event_id}'
        
        values = {
            'event': event,
            'badge_bg_url': badge_bg_url,
        }
        
        _logger.info(f"Rendering registration page for event: {event.title_name} (ID: {event_id})")
        return request.render('vac_social_marketing.event_registration_template', values)

    @http.route('/event/invite/<int:event_id>/preview', type='http', auth='user', website=True)
    def event_registration_preview(self, event_id, **kwargs):
        """
        Backend-only preview of the event registration page.
        Requires an authenticated internal user (auth='user').
        Bypasses the published check so admins can review the form
        before going live.

        Args:
            event_id: ID of the event

        Returns:
            Rendered registration template regardless of published state
        """
        event = request.env['vac.event'].sudo().browse(event_id)

        if not event.exists():
            _logger.warning(f"Preview: Event {event_id} not found")
            return request.render('vac_social_marketing.event_not_found')

        badge_bg_url = None
        if event.badge_background:
            badge_bg_url = f'/event/badge/{event_id}'

        values = {
            'event': event,
            'badge_bg_url': badge_bg_url,
            'is_preview': True,   # template can show a "preview" banner if desired
        }

        _logger.info(
            f"Preview: rendering registration form for event '{event.title_name}' "
            f"(ID: {event_id}, published={event.published})"
        )
        return request.render('vac_social_marketing.event_registration_template', values)
    
    
    @http.route('/event/badge/<int:event_id>', type='http', auth='public')
    def get_event_badge_background(self, event_id, **kwargs):
        """
        Serve the badge background image for an event
        
        Args:
            event_id: ID of the event
            
        Returns:
            Image binary data with appropriate headers
        """
        event = request.env['vac.event'].sudo().browse(event_id)
        
        if not event.exists() or not event.badge_background:
            # Return 404 if no image found
            return request.not_found()
        
        # Decode base64 image
        image_data = base64.b64decode(event.badge_background)
        
        # Determine content type from filename or default to png
        content_type = 'image/png'
        if event.badge_background_filename:
            filename = event.badge_background_filename.lower()
            if filename.endswith('.jpg') or filename.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif filename.endswith('.gif'):
                content_type = 'image/gif'
            elif filename.endswith('.webp'):
                content_type = 'image/webp'
            elif filename.endswith('.svg'):
                content_type = 'image/svg+xml'
        
        # Return image with proper headers
        headers = [
            ('Content-Type', content_type),
            ('Content-Length', len(image_data)),
            ('Cache-Control', 'public, max-age=604800'),  # Cache for 1 week
        ]
        
        return request.make_response(image_data, headers)
    
    
    @http.route('/event/register/submit', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def event_registration_submit(self, **post):
        """
        Handle event registration form submission
        
        Args:
            post: Form data containing event_id, name, email, phone, company, notes
            
        Returns:
            Redirect to success page or back to form with error
        """
        try:
            event_id = int(post.get('event_id'))
        except (ValueError, TypeError):
            _logger.error("Invalid event_id in registration submission")
            return request.render('vac_social_marketing.event_not_found')
        
        # Validate required fields
        if not all([post.get('name'), post.get('email'), post.get('phone')]):
            _logger.warning(f"Missing required fields for event {event_id}")
            return request.redirect(f'/event/invite/{event_id}?error=missing_fields')
        
        try:
            # Prepare lead values
            lead_vals = {
                'event_id': event_id,
                'name': post.get('name'),
                'email': post.get('email'),
                'phone': post.get('phone'),
                'company': post.get('company', ''),
                'notes': post.get('notes', ''),
            }
            
            # Get default stage (New, Registered, or Draft)
            default_stage = request.env['vac.event.lead.stage'].sudo().search([
                ('name', 'in', ['New', 'Registered', 'Draft'])
            ], order='sequence', limit=1)
            
            if default_stage:
                lead_vals['stage_id'] = default_stage.id
            else:
                _logger.warning("No default lead stage found")
            
            # Create the lead
            lead = request.env['vac.event.lead'].sudo().create(lead_vals)
            
            _logger.info(f"Lead created successfully: {lead.name} (ID: {lead.id}) for event: {event_id}")
            
            return request.redirect(f'/event/register/success?event_id={event_id}&lead_id={lead.id}')
            
        except Exception as e:
            _logger.error(f"Error creating lead for event {event_id}: {str(e)}", exc_info=True)
            return request.redirect(f'/event/invite/{event_id}?error=registration_failed')
    
    
    @http.route('/event/register/success', type='http', auth='public', website=True)
    def registration_success(self, **kwargs):
        """
        Display success page after registration
        
        Args:
            kwargs: Contains event_id and lead_id
            
        Returns:
            Rendered success template
        """
        try:
            event_id = int(kwargs.get('event_id', 0))
            lead_id = int(kwargs.get('lead_id', 0))
        except (ValueError, TypeError):
            _logger.error("Invalid event_id or lead_id in success page")
            return request.render('vac_social_marketing.event_not_found')
        
        event = request.env['vac.event'].sudo().browse(event_id)
        lead = request.env['vac.event.lead'].sudo().browse(lead_id)
        
        # Validate event and lead exist
        if not event.exists() or not lead.exists():
            _logger.error(f"Event {event_id} or Lead {lead_id} not found")
            return request.render('vac_social_marketing.event_not_found')
        
        # Prepare badge background URL if exists
        badge_bg_url = None
        if event.badge_background:
            badge_bg_url = f'/event/badge/{event_id}'
        
        values = {
            'event': event,
            'lead': lead,
            'badge_bg_url': badge_bg_url,
        }
        
        _logger.info(f"Displaying success page for lead: {lead.name} (ID: {lead_id})")
        return request.render('vac_social_marketing.event_registration_success', values)

    # ─────────────────────────────────────────────────────────────────
    #  Shared helper — build a bare-HTML print page (no Odoo layout)
    # ─────────────────────────────────────────────────────────────────
    def _build_print_qr_html(self, title, link, qr_url):
        """Return a self-contained HTML string that auto-triggers window.print().
        Uses inline base64 QR so nothing can be blocked by the browser.
        No Odoo layout wrappers — pure HTML/CSS/JS only.
        """
        link_block = ''
        if link:
            link_block = f'''
            <div class="link-label">Registration Link</div>
            <div class="link-box">{link}</div>'''

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} — QR Code</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html, body {{
      width: 100%; height: 100%;
      background: #ffffff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
      color: #111827;
    }}

    .wrap {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 48px 24px;
      text-align: center;
    }}

    h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; }}
    .sub {{ font-size: 13px; color: #6b7280; margin-bottom: 32px; }}

    .card {{
      display: inline-block;
      padding: 18px;
      background: #fff;
      border: 2px solid #d1d5db;
      border-radius: 14px;
      margin-bottom: 28px;
    }}

    .card img {{
      display: block;
      width: 240px;
      height: 240px;
    }}

    .hint {{
      font-size: 12px;
      color: #6b7280;
      font-style: italic;
      margin-top: 8px;
    }}

    .link-label {{
      font-size: 11px;
      font-weight: 600;
      color: #374151;
      text-transform: uppercase;
      letter-spacing: .6px;
      margin-bottom: 6px;
    }}

    .link-box {{
      max-width: 480px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 10px 16px;
      font-size: 13px;
      color: #1d4ed8;
      word-break: break-all;
      margin-bottom: 32px;
    }}

    .no-print {{
      font-size: 12px;
      color: #9ca3af;
      margin-top: 8px;
    }}

    @media print {{
      .no-print {{ display: none !important; }}
      html, body {{ background: #fff !important; }}
      .card {{ border-color: #aaa; }}
      * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{title}</h1>
    <div class="sub">Registration QR Code</div>

    <div class="card">
      <img src="{qr_url}" alt="QR Code" id="qr-img"/>
      <div class="hint">Scan to open the registration form</div>
    </div>

    {link_block}

    <div class="no-print">
      Press <strong>Ctrl+P</strong> (or <strong>⌘+P</strong> on Mac) and choose
      <em>Save as PDF</em> to export.
    </div>
  </div>

  <script>
    // Wait for the QR image to fully load before triggering print
    var img = document.getElementById('qr-img');
    function doPrint() {{ window.print(); }}
    if (img.complete) {{
      setTimeout(doPrint, 400);
    }} else {{
      img.addEventListener('load', function() {{ setTimeout(doPrint, 400); }});
      img.addEventListener('error', function() {{ setTimeout(doPrint, 400); }});
    }}
  </script>
</body>
</html>'''

    # ─────────────────────────────────────────────────────────────────
    #  Print-as-PDF page for Event QR code
    # ─────────────────────────────────────────────────────────────────
    @http.route('/event/print-qr/<int:event_id>', type='http', auth='user')
    def event_print_qr(self, event_id, **kwargs):
        """Serve a bare-HTML print page for the event QR code."""
        event = request.env['vac.event'].sudo().browse(event_id)
        if not event.exists() or not event.qr_code:
            return request.not_found()
        qr_url = f'/web/image/vac.event/{event_id}/qr_code'
        html = self._build_print_qr_html(
            title=event.title_name or 'Event',
            link=event.event_link or '',
            qr_url=qr_url,
        )
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    # ─────────────────────────────────────────────────────────────────
    #  Print-as-PDF page for Social Campaign QR code
    # ─────────────────────────────────────────────────────────────────
    @http.route('/social/print-qr/<string:model>/<int:record_id>', type='http', auth='user')
    def social_print_qr(self, model, record_id, **kwargs):
        """Serve a bare-HTML print page for the campaign QR code."""
        allowed_models = {'vac.social.fb', 'vac.social.ing'}
        if model not in allowed_models:
            return request.not_found()
        record = request.env[model].sudo().browse(record_id)
        if not record.exists() or not record.qr_code:
            return request.not_found()
        qr_url = f'/web/image/{model}/{record_id}/qr_code'
        link = getattr(record, 'social_link', None) or ''
        html = self._build_print_qr_html(
            title=getattr(record, 'name', '') or 'Campaign',
            link=link,
            qr_url=qr_url,
        )
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])
