# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import base64
import json
import threading
from .lead_mapping import finalize_lead_values, route_registration_value

_logger = logging.getLogger(__name__)


class VacEventController(http.Controller):

    # ─────────────────────────────────────────────────────────────────
    #  Helper — dynamic sender e-mail
    # ─────────────────────────────────────────────────────────────────
    def _get_sender_email(self):
        """
        Return the outgoing e-mail address configured in Odoo.

        Priority:
          1. res.config.settings  →  email_from   (Settings → Technical → Outgoing Mail)
          2. ir.config_parameter  →  mail.default.from
          3. The company's e-mail address
          4. Hard-coded fallback (safety net — should never be reached in production)
        """
        try:
            # 1. Settings email_from (most user-visible place in Odoo UI)
            email_from = request.env['ir.config_parameter'].sudo().get_param(
                'mail.default.from'
            )
            if email_from:
                return email_from
        except Exception as e:
            _logger.warning(f"[sender] ir.config_parameter lookup failed: {e}")

        try:
            # 2. Company e-mail
            company_email = request.env.company.email
            if company_email:
                return company_email
        except Exception as e:
            _logger.warning(f"[sender] company email lookup failed: {e}")

        # 3. Absolute fallback — log a warning so the admin knows to configure it
        _logger.warning(
            "[sender] No outgoing e-mail found in Odoo settings. "
            "Go to Settings → Technical → Outgoing Mail Servers and set a default."
        )
        return False

    # ─────────────────────────────────────────────────────────────────
    #  Helper — resolve cover photo
    # ─────────────────────────────────────────────────────────────────
    def _resolve_cover_photo(self, event_id):
        standard_url = f'/event/cover/{event_id}'

        try:
            attach = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'vac.event'),
                ('res_id',    '=', event_id),
                ('res_field', '=', 'cover_photo'),
            ], limit=1)
            if attach:
                return True, standard_url
        except Exception as e:
            _logger.warning(f"[cover] Method 1 failed: {e}")

        try:
            attach = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'vac.event'),
                ('res_id',    '=', event_id),
                ('mimetype',  'like', 'image/'),
            ], limit=1, order='id desc')
            if attach:
                return True, standard_url
        except Exception as e:
            _logger.warning(f"[cover] Method 2 failed: {e}")

        try:
            event = request.env['vac.event'].with_context(
                active_test=False).sudo().browse(event_id)
            if event.exists() and event.cover_photo:
                return True, standard_url
        except Exception as e:
            _logger.warning(f"[cover] Method 3 failed: {e}")

        return False, None

    def _detect_content_type(self, filename):
        fn = (filename or '').lower()
        if fn.endswith(('.jpg', '.jpeg')): return 'image/jpeg'
        if fn.endswith('.gif'):            return 'image/gif'
        if fn.endswith('.webp'):           return 'image/webp'
        if fn.endswith('.svg'):            return 'image/svg+xml'
        return 'image/png'

    def _load_event_sudo(self, event_id):
        """
        Load event via raw SQL — completely bypasses ORM, website mixin,
        active_test, and any published filters.

        Returns:
          (None, None)    → row missing entirely OR archived  → show 404
          (event, False)  → active + unpublished              → show sold-out page
          (event, True)   → active + published                → show register page
        """
        try:
            request.env.cr.execute(
                "SELECT id, published, active FROM vac_event WHERE id = %s",
                (event_id,)
            )
            row = request.env.cr.fetchone()

            if not row:
                _logger.info(f"[load_event] Event {event_id}: not in DB")
                return None, None

            db_id, is_published, is_active = row
            _logger.info(
                f"[load_event] Event {event_id}: "
                f"active={is_active}, published={is_published}"
            )

            if not is_active:
                _logger.info(f"[load_event] Event {event_id}: archived → 404")
                return None, None

            event = request.env['vac.event'].with_context(
                active_test=False
            ).sudo().browse(event_id)

            return event, bool(is_published)

        except Exception as e:
            _logger.error(f"[load_event] SQL failed: {e}", exc_info=True)
            return None, None

    # ─────────────────────────────────────────────────────────────────
    #  Public event listing
    # ─────────────────────────────────────────────────────────────────
    @http.route(['/event', '/events'], type='http', auth='public', website=True)
    def event_listing(self, **kwargs):
        events = request.env['vac.event'].sudo().search([
            ('published', '=', True),
            ('active',    '=', True),
        ], order='date asc')
        return request.render(
            'vac_social_marketing.event_listing_page', {'events': events}
        )

    # ─────────────────────────────────────────────────────────────────
    #  Registration page  (GET)
    # ─────────────────────────────────────────────────────────────────
    @http.route(
        ['/event/invite/<int:event_id>',
         '/event/invite/<string:event_slug>'],
        type='http',
        auth='public',
        website=True,
        sitemap=False,
    )
    def event_registration_page(self, event_id=None, event_slug=None, **kwargs):
        # Resolve slug (title-based) to event id
        if event_slug and event_id is None:
            import re
            slug_normalized = re.sub(r'[^a-z0-9]+', '-', event_slug.lower()).strip('-')
            all_events = request.env['vac.event'].sudo().search([('active', '=', True)])
            event_id = None
            for ev in all_events:
                ev_slug = re.sub(r'[^a-z0-9]+', '-', (ev.title_name or '').lower()).strip('-')
                if ev_slug == slug_normalized:
                    event_id = ev.id
                    break
            if not event_id:
                return request.not_found()
        event, is_published = self._load_event_sudo(event_id)

        # ── CASE 1: Truly missing or archived ────────────────────────────────
        if event is None:
            return request.render(
                'vac_social_marketing.event_not_found', {'event': None}
            )

        # ── CASE 2: Active but unpublished ───────────────────────────────────
        if not is_published:
            return request.render(
                'vac_social_marketing.event_not_found', {'event': event}
            )

        # ── CASE 3: Published → normal registration page ──────────────────────
        has_badge_image = bool(event.badge_background)
        has_cover_photo, cover_photo_url = self._resolve_cover_photo(event_id)

        # ─── resolve default branch service for pre-selection ────────────
        default_service = request.env['branch.service'].sudo().search(
            [('is_default', '=', True)], limit=1
        )

        _logger.info(
            f"[page] Event {event_id} '{event.title_name}': published=True"
        )

        values = {
            'event'          : event,
            'event_id'       : event_id,
            'background_url' : f'/event/badge/{event_id}' if has_badge_image else None,
            'badge_image_url': f'/event/badge/{event_id}' if has_badge_image else None,
            'has_badge_image': has_badge_image,
            'cover_photo_url': cover_photo_url,
            'has_cover_photo': has_cover_photo,
            'is_sold_out'    : False,
            'default_service': default_service,
        }
        return request.render(
            'vac_social_marketing.event_registration_template', values
        )

    # ─────────────────────────────────────────────────────────────────
    #  Badge image serving
    # ─────────────────────────────────────────────────────────────────
    @http.route('/event/badge/<int:event_id>', type='http', auth='public')
    def get_event_badge_background(self, event_id, **kwargs):
        event = request.env['vac.event'].with_context(
            active_test=False).sudo().browse(event_id)
        if not event.exists() or not event.badge_background:
            return request.not_found()
        try:
            image_data   = base64.b64decode(event.badge_background)
            content_type = self._detect_content_type(
                getattr(event, 'badge_background_filename', '') or ''
            )
            return request.make_response(image_data, [
                ('Content-Type',   content_type),
                ('Content-Length', len(image_data)),
                ('Cache-Control',  'public, max-age=604800'),
            ])
        except Exception as e:
            _logger.error(f"Badge serve error: {e}", exc_info=True)
            return request.not_found()

    # ─────────────────────────────────────────────────────────────────
    #  Cover photo serving — fallback route
    # ─────────────────────────────────────────────────────────────────
    @http.route('/event/cover/<int:event_id>', type='http', auth='public')
    def get_event_cover_photo(self, event_id, **kwargs):
        image_data   = None
        content_type = 'image/png'

        try:
            event = request.env['vac.event'].with_context(
                active_test=False).sudo().browse(event_id)
            if event.exists() and event.cover_photo:
                image_data = base64.b64decode(event.cover_photo)
        except Exception as e:
            _logger.warning(f"[cover-serve] ORM read failed: {e}")

        if not image_data:
            try:
                attach = request.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'vac.event'),
                    ('res_id',    '=', event_id),
                    ('res_field', '=', 'cover_photo'),
                ], limit=1)
                if attach:
                    raw = attach.sudo()._file_read(attach.store_fname) \
                        if attach.store_fname else attach.datas
                    if raw:
                        image_data   = base64.b64decode(raw) if isinstance(raw, str) else raw
                        content_type = attach.mimetype or 'image/png'
            except Exception as e:
                _logger.warning(f"[cover-serve] attachment (res_field) failed: {e}")

        if not image_data:
            try:
                attach = request.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'vac.event'),
                    ('res_id',    '=', event_id),
                    ('mimetype',  'like', 'image/'),
                ], limit=1, order='id desc')
                if attach:
                    raw = attach.sudo()._file_read(attach.store_fname) \
                        if attach.store_fname else attach.datas
                    if raw:
                        image_data   = base64.b64decode(raw) if isinstance(raw, str) else raw
                        content_type = attach.mimetype or 'image/png'
            except Exception as e:
                _logger.warning(f"[cover-serve] attachment (any image) failed: {e}")

        if not image_data:
            return request.not_found()

        return request.make_response(image_data, [
            ('Content-Type',   content_type),
            ('Content-Length', len(image_data)),
            ('Cache-Control',  'public, max-age=86400'),
        ])

    # ─────────────────────────────────────────────────────────────────
    #  DEBUG route
    # ─────────────────────────────────────────────────────────────────
    @http.route('/event/debug/<int:event_id>', type='http', auth='user')
    def debug_event_images(self, event_id, **kwargs):
        event, is_published = self._load_event_sudo(event_id)
        all_attach = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'vac.event'),
            ('res_id',    '=', event_id),
        ])
        lines = [
            f"Event ID       : {event_id}",
            f"Found          : {event is not None}",
            f"is_published   : {is_published}",
            f"is_sold_out    : {not is_published if is_published is not None else 'N/A'}",
            f"Title          : {event.title_name if event else 'N/A'}",
            f"",
            f"Attachments ({len(all_attach)} total):",
        ]
        for a in all_attach:
            lines.append(
                f"  id={a.id} | res_field={a.res_field!r} | "
                f"mimetype={a.mimetype} | store_fname={a.store_fname!r}"
            )
        has_cover, url = self._resolve_cover_photo(event_id)
        lines += [
            f"",
            f"cover → has={has_cover}, url={url}",
        ]
        return request.make_response(
            '\n'.join(lines),
            [('Content-Type', 'text/plain; charset=utf-8')]
        )

    # ─────────────────────────────────────────────────────────────────
    #  Registration form  (POST)
    # ─────────────────────────────────────────────────────────────────
    @http.route(
        '/event/register/submit/<int:event_id>',
        type='http', auth='public', website=True,
        methods=['POST'], csrf=True,
    )
    def event_registration_submit(self, event_id, **kwargs):
        _logger.info(f"=== SUBMIT event_id={event_id} ===")

        event, is_published = self._load_event_sudo(event_id)

        if event is None:
            return request.render('vac_social_marketing.event_not_found', {'event': None})

        if not is_published:
            return request.redirect(f'/event/invite/{event_id}')

        lead_vals      = {'event_id': event_id}
        custom_answers = {}

        for field in event.registration_field_ids:
            post_key = f'custom_{field.id}'

            if field.field_type == 'checkbox':
                raw   = request.httprequest.form.get(post_key, '')
                value = '1' if raw else '0'
            else:
                value = request.httprequest.form.get(post_key, '').strip()

            if field.is_required and not value:
                _logger.warning(
                    f"Required field missing: id={field.id} label={field.label!r}")
                return request.redirect(
                    f'/event/invite/{event_id}?error=missing_fields')

            route_registration_value(
                request.env,
                field,
                value,
                lead_vals,
                custom_answers,
            )

        finalize_lead_values(lead_vals)

        if not lead_vals.get('name'):
            _logger.warning("No field mapped to Lead → Full Name")
            return request.redirect(
                f'/event/invite/{event_id}?error=missing_fields')

        try:
            lead_model   = request.env['vac.event.lead'].sudo()
            model_fields = lead_model._fields

            safe_vals = {
                k: v for k, v in lead_vals.items()
                if k in ('event_id', 'branch_service_id') or k in model_fields
            }

            if 'platform' in model_fields:
                safe_vals['platform'] = 'event'

            if 'custom_field_answers' in model_fields and custom_answers:
                safe_vals['custom_field_answers'] = json.dumps(
                    custom_answers, ensure_ascii=False
                )

            if 'stage_id' in model_fields:
                stage = request.env['vac.event.lead.stage'].sudo().search(
                    [('name', '=', 'New Lead')], limit=1)
                if not stage:
                    stage = request.env['vac.event.lead.stage'].sudo().search(
                        [], order='sequence', limit=1)
                if stage:
                    safe_vals['stage_id'] = stage.id

            if 'status_id' in model_fields:
                status = request.env['vac.event.lead.status'].sudo().search(
                    [('name', '=', 'Active')], limit=1)
                if not status:
                    status = request.env['vac.event.lead.status'].sudo().search(
                        [], order='name', limit=1)
                if status:
                    safe_vals['status_id'] = status.id

            if 'branch_service_id' not in safe_vals and 'branch_service_id' in model_fields:
                default_svc = request.env['branch.service'].sudo().search(
                    [('is_default', '=', True)], limit=1)
                if default_svc:
                    safe_vals['branch_service_id'] = default_svc.id

            lead = lead_model.create(safe_vals)
            _logger.info(f"Lead created: {lead.name} ID={lead.id}")
            self._send_registration_email(lead, event, custom_answers)

            return request.redirect(
                f'/event/register/success?event_id={event_id}&lead_id={lead.id}'
            )

        except Exception as e:
            _logger.error(f"Lead creation error: {e}", exc_info=True)
            return request.redirect(
                f'/event/invite/{event_id}?error=registration_failed')

    # ─────────────────────────────────────────────────────────────────
    #  Confirmation e-mail
    # ─────────────────────────────────────────────────────────────────
    def _send_registration_email(self, lead, event, custom_answers=None):
        from datetime import datetime

        # ── Dynamic sender: reads from Odoo settings, not hardcoded ──────────
        SENDER = self._get_sender_email()

        try:
            # ── PRIORITY 1: Dynamically built template (Configuration → Email Templates) ──
            if event.sudo().email_config_id:
                event.sudo().email_config_id.send_email(lead, event, sender_email=SENDER)
                return

            # ── PRIORITY 2: Legacy mail.template chosen on the event ──────────
            template = event.sudo().mail_template_id or None

            # ── PRIORITY 3: Module-level default template (XML data) ──────────
            if not template:
                template = request.env.ref(
                    'vac_social_marketing.email_template_event_registration',
                    raise_if_not_found=False,
                )

            if template:
                email_values = {'email_from': SENDER} if SENDER else {}
                if lead.email:
                    email_values['email_to'] = lead.email
                template.sudo().send_mail(
                    lead.id, force_send=True,
                    email_values=email_values,
                )
                return

            def row(label, value, is_badge=False):
                """Render a detail row. Returns '' if value is empty."""
                if value in (None, '', False):
                    return ''
                badge_html = (
                    f'<span style="display:inline-block;background:#e8f5e9;'
                    f'color:#2e7d32;padding:3px 10px;border-radius:20px;'
                    f'font-size:13px;font-weight:600;">{value}</span>'
                ) if is_badge else f'<span style="font-size:14px;color:#333;">{value}</span>'
                return f'''
                <tr>
                  <td style="padding:11px 18px;border-bottom:1px solid #f0f0f0;
                             background:#fafafa;width:38%;vertical-align:top;">
                    <span style="font-size:11px;font-weight:700;letter-spacing:.5px;
                                 text-transform:uppercase;color:#888;">{label}</span>
                  </td>
                  <td style="padding:11px 18px;border-bottom:1px solid #f0f0f0;
                             vertical-align:top;">
                    {badge_html}
                  </td>
                </tr>'''

            def bool_row(label, flag):
                """Only render a row when the flag is True."""
                return row(label, 'Yes', is_badge=True) if flag else ''

            email_link = (
                f'<a href="mailto:{lead.email}" '
                f'style="color:#003366;font-weight:600;text-decoration:none;">'
                f'{lead.email}</a>'
            ) if lead.email else ''

            event_date = (
                event.date_begin.strftime('%B %d, %Y  •  %I:%M %p')
                if event.date_begin else ''
            )

            branch_service_name = (
                lead.branch_service_id.name if lead.branch_service_id else ''
            )

            va_rating = (
                str(int(lead.current_va_disability_rating)) + '%'
                if lead.current_va_disability_rating else ''
            )

            detail_rows = (
                row('Full Name',                     lead.name or '')
              + row('Email Address',                 email_link)
              + row('Mobile / Phone',                getattr(lead, 'mobile', '') or '')
              + row('WhatsApp Number',               getattr(lead, 'whatsapp_number', '') or '')
              + row('Branch / Service',              branch_service_name)
              + row('VA Disability Rating',          va_rating)
              + bool_row('US Veteran',               lead.is_veteran)
              + bool_row('Has DD214 Access',         lead.has_dd214_copy or lead.has_dd214_access)
              + bool_row('Current VAC Client',       lead.is_current_client)
              + bool_row('Bringing a Plus One',      lead.is_bringing_plus_one)
              + row('Physical Address',              getattr(lead, 'physical_address', '') or '')
              + row('Event',                         event.title_name or '')
              + row('Event Date',                    event_date)
            )

            for data in (custom_answers or {}).values():
                val = data.get('value', '')
                if data.get('type') == 'checkbox':
                    if val == '1' and data.get('label'):
                        detail_rows += row(data['label'], 'Yes', is_badge=True)
                elif data.get('label') and val:
                    detail_rows += row(data['label'], val)

            body_html = f"""
            <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:620px;
                        margin:0 auto;background:#ffffff;border-radius:12px;
                        overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10);">

                <!-- HEADER -->
                <div style="background:linear-gradient(135deg,#002855 0%,#7b0020 100%);
                            padding:36px 32px;text-align:center;">
                    <div style="font-size:32px;margin-bottom:8px;">🇺🇸</div>
                    <h1 style="color:#ffffff;margin:0 0 6px;font-size:24px;
                               font-weight:800;letter-spacing:0.5px;
                               text-shadow:0 1px 3px rgba(0,0,0,0.3);">
                        Veterans Advocate Center
                    </h1>
                    <p style="color:rgba(255,255,255,0.75);margin:0;
                               font-size:11px;letter-spacing:3px;
                               text-transform:uppercase;font-weight:500;">
                        Event Registration Confirmation
                    </p>
                </div>

                <!-- CONFIRMED BADGE -->
                <div style="text-align:center;padding:30px 32px 4px;">
                    <div style="display:inline-block;background:#003366;
                                color:#ffffff;padding:12px 36px;
                                border-radius:50px;font-size:13px;
                                font-weight:700;letter-spacing:2px;
                                text-transform:uppercase;">
                        ✔&nbsp;&nbsp;Registration Confirmed
                    </div>
                </div>

                <!-- BODY -->
                <div style="padding:24px 32px 32px;">
                    <h2 style="color:#002855;margin:0 0 8px;font-size:24px;font-weight:700;">
                        Thank You, {lead.name}!
                    </h2>
                    <p style="font-size:15px;line-height:1.75;color:#555;margin:0 0 28px;">
                        We have successfully received your registration for
                        <strong style="color:#002855;">{event.title_name}</strong>.
                        Our team will review your information and reach out to you shortly.
                    </p>

                    <!-- DETAILS TABLE -->
                    <div style="border:1px solid #e8edf3;border-radius:10px;
                                overflow:hidden;margin-bottom:28px;">
                        <div style="background:linear-gradient(90deg,#002855,#003f80);
                                    padding:13px 18px;">
                            <span style="font-size:11px;font-weight:700;
                                         letter-spacing:2.5px;color:#ffffff;
                                         text-transform:uppercase;">
                                📋 &nbsp;Submission Details
                            </span>
                        </div>
                        <table style="width:100%;border-collapse:collapse;background:#fff;">
                            {detail_rows}
                        </table>
                    </div>

                    <p style="font-size:14px;line-height:1.75;color:#666;margin:0 0 6px;">
                        If you have any questions or need immediate assistance,
                        please don't hesitate to contact us.
                    </p>
                    <p style="font-size:15px;line-height:1.75;color:#333;margin:0;">
                        <strong>Best regards,</strong><br/>
                        <span style="color:#002855;font-weight:600;">
                            Veterans Advocate Center Team
                        </span>
                    </p>
                </div>

                <!-- FOOTER -->
                <div style="background:#002855;padding:26px 20px;text-align:center;">
                    <p style="color:#ffffff;margin:0 0 4px;font-size:16px;font-weight:700;">
                        🇺🇸 Veterans Advocate Center
                    </p>
                    <p style="color:rgba(255,255,255,0.65);margin:0 0 14px;font-size:13px;">
                        Serving those who served us
                    </p>
                    <p style="color:rgba(255,255,255,0.5);margin:0;font-size:11px;">
                        © {datetime.now().year} Veterans Advocate Center. All rights reserved.
                        &nbsp;|&nbsp;
                        <a href="https://veteransadvocatecenter.com/"
                           style="color:rgba(255,255,255,0.8);text-decoration:none;">
                            Visit Our Website
                        </a>
                    </p>
                </div>

            </div>"""

            mail_vals = {
                'subject'    : f'Registration Confirmed – {event.title_name}',
                'body_html'  : body_html,
                'email_to'   : lead.email,
                'auto_delete': True,
            }
            if SENDER:
                mail_vals['email_from'] = SENDER

            dbname     = request.env.cr.dbname
            _mail_vals = dict(mail_vals)

            def _send_bg():
                try:
                    import odoo
                    with odoo.registry(dbname).cursor() as cr:
                        env2 = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                        mail = env2['mail.mail'].create(_mail_vals)
                        mail.send()
                except Exception as exc:
                    _logger.error(f"[individual bg-mail] send failed: {exc}", exc_info=True)

            threading.Thread(target=_send_bg, daemon=True).start()

        except Exception as e:
            _logger.error(f"Email error: {e}", exc_info=True)

    # ─────────────────────────────────────────────────────────────────
    #  Success page  (GET)
    # ─────────────────────────────────────────────────────────────────
    @http.route('/event/register/success', type='http', auth='public', website=True)
    def registration_success(self, **kwargs):
        try:
            event_id = int(kwargs.get('event_id', 0))
            lead_id  = int(kwargs.get('lead_id',  0))
        except (ValueError, TypeError):
            return request.render(
                'vac_social_marketing.event_not_found', {'event': None})

        event = request.env['vac.event'].with_context(
            active_test=False).sudo().browse(event_id)
        lead  = request.env['vac.event.lead'].sudo().browse(lead_id)

        if not event.exists() or not lead.exists():
            return request.render(
                'vac_social_marketing.event_not_found',
                {'event': event if event.exists() else None})

        return request.render(
            'vac_social_marketing.event_registration_success',
            {'event': event, 'lead': lead},
        )