# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import threading
import logging
import json
import base64
from .lead_mapping import finalize_lead_values, route_registration_value

_logger = logging.getLogger(__name__)

_PLATFORM_MAP = {
    'fb':     'vac.social.fb',
    'ing':    'vac.social.ing',
    'office': 'vac.social.office',
}

# Maps URL platform key → vac.event.lead platform selection value
_PLATFORM_LEAD_VALUE = {
    'fb':     'facebook',
    'ing':    'instagram',
    'office': 'office',
}

_PLATFORM_LABELS = {'fb': 'Facebook', 'ing': 'Instagram', 'office': 'Offices'}
_PLATFORM_ACCENTS = {'fb': '#1877F2', 'ing': '#E1306C', 'office': '#0d6efd'}

class VacSocialController(http.Controller):

    # ─────────────────────────────────────────────────────────────────
    #  Helper — dynamic sender e-mail
    # ─────────────────────────────────────────────────────────────────
    def _get_sender_email(self):
        """
        Return the outgoing e-mail address configured in Odoo.

        Priority:
          1. ir.config_parameter  →  mail.default.from
             (Settings → Technical → Parameters → System Parameters)
          2. The company's e-mail address
          3. Returns False — logs a warning so the admin knows to configure it
        """
        try:
            email_from = request.env['ir.config_parameter'].sudo().get_param(
                'mail.default.from'
            )
            if email_from:
                return email_from
        except Exception as e:
            _logger.warning(f"[sender] ir.config_parameter lookup failed: {e}")

        try:
            company_email = request.env.company.email
            if company_email:
                return company_email
        except Exception as e:
            _logger.warning(f"[sender] company email lookup failed: {e}")

        _logger.warning(
            "[sender] No outgoing e-mail found in Odoo settings. "
            "Go to Settings → Technical → Outgoing Mail Servers and set a default."
        )
        return False

    def _detect_content_type(self, filename):
        fn = (filename or '').lower()
        if fn.endswith(('.jpg', '.jpeg')):
            return 'image/jpeg'
        if fn.endswith('.gif'):
            return 'image/gif'
        if fn.endswith('.webp'):
            return 'image/webp'
        if fn.endswith('.svg'):
            return 'image/svg+xml'
        return 'image/png'

    def _get_social_record(self, platform, record_id):
        """Legacy lookup by integer ID (kept for backward compatibility)."""
        model = _PLATFORM_MAP.get(platform)
        if not model:
            return None
        rec = request.env[model].sudo().browse(record_id)
        if not rec.exists() or not rec.published:
            return None
        return rec

    def _get_social_record_by_slug(self, platform, slug):
        """Lookup by URL slug (campaign name). Falls back to ID if slug is numeric."""
        model = _PLATFORM_MAP.get(platform)
        if not model:
            return None
        # Support legacy numeric IDs in existing bookmarked links
        if slug.isdigit():
            return self._get_social_record(platform, int(slug))
        rec = request.env[model].sudo().search([("slug", "=", slug)], limit=1)
        if not rec or not rec.published:
            return None
        return rec

    # ─────────────────────────────────────────────────────────────────
    #  Registration page  (GET)
    # ─────────────────────────────────────────────────────────────────
    @http.route(
        '/social/<string:platform>/invite/<string:slug>',
        type='http', auth='public', website=True,
    )
    def social_registration_page(self, platform, slug, **kwargs):
        rec = self._get_social_record_by_slug(platform, slug)
        if not rec:
            return request.render('vac_social_marketing.social_not_found')

        platform_label = _PLATFORM_LABELS.get(platform, platform)

        # ─── resolve default branch service for pre-selection ────────────
        default_service = request.env['branch.service'].sudo().search(
            [('is_default', '=', True)], limit=1
        )

        return request.render('vac_social_marketing.social_registration_template', {
            'record':          rec,
            'platform':        platform,
            'platform_label':  platform_label,
            'default_service': default_service,
        })

    # ─────────────────────────────────────────────────────────────────
    #  Registration page — BACKEND PREVIEW  (GET, auth='user')
    #  Identical to the public page but skips the published check so
    #  admins can review the full form before going live.
    # ─────────────────────────────────────────────────────────────────
    @http.route(
        '/social/<string:platform>/invite/<string:slug>/preview',
        type='http', auth='user', website=True,
    )
    def social_registration_preview(self, platform, slug, **kwargs):
        """
        Backend-only preview of the social campaign registration page.
        Requires an authenticated internal user (auth='user').
        Bypasses the published check so admins can see the full
        registration form before publishing.
        """
        model = _PLATFORM_MAP.get(platform)
        if not model:
            return request.render('vac_social_marketing.social_not_found')

        # Look up by slug (or legacy numeric ID) — no published check
        if slug.isdigit():
            rec = request.env[model].sudo().browse(int(slug))
            if not rec.exists():
                return request.render('vac_social_marketing.social_not_found')
        else:
            rec = request.env[model].sudo().search([('slug', '=', slug)], limit=1)
            if not rec:
                return request.render('vac_social_marketing.social_not_found')

        platform_label = _PLATFORM_LABELS.get(platform, platform)

        default_service = request.env['branch.service'].sudo().search(
            [('is_default', '=', True)], limit=1
        )

        return request.render('vac_social_marketing.social_registration_template', {
            'record':          rec,
            'platform':        platform,
            'platform_label':  platform_label,
            'default_service': default_service,
            'is_preview':      True,   # template can show a preview banner if desired
        })

    @http.route(
        '/social/<string:platform>/cover/<int:record_id>',
        type='http', auth='public'
    )
    def get_social_cover_photo(self, platform, record_id, **kwargs):
        model = _PLATFORM_MAP.get(platform)
        if not model:
            return request.not_found()

        record = request.env[model].with_context(active_test=False).sudo().browse(record_id)
        if not record.exists() or not record.cover_photo:
            return request.not_found()

        try:
            raw = record.cover_photo
            if isinstance(raw, bytes):
                try:
                    raw.decode('ascii')
                    image_data = base64.b64decode(raw)
                except UnicodeDecodeError:
                    image_data = raw
            else:
                image_data = base64.b64decode(raw)
            content_type = 'image/png'
            return request.make_response(image_data, [
                ('Content-Type', content_type),
                ('Content-Length', len(image_data)),
                ('Cache-Control', 'public, max-age=86400'),
            ])
        except Exception as e:
            _logger.error(f"Social cover serve error: {e}", exc_info=True)
            return request.not_found()

    # ─────────────────────────────────────────────────────────────────
    #  Form submit  (POST)
    # ─────────────────────────────────────────────────────────────────
    @http.route(
        '/social/<string:platform>/register/submit/<string:slug>',
        type='http', auth='public', website=True,
        methods=['POST'], csrf=True,
    )
    def social_registration_submit(self, platform, slug, **kwargs):
        _logger.info(f"=== SOCIAL SUBMIT platform={platform} slug={slug} ===")

        rec = self._get_social_record_by_slug(platform, slug)
        if not rec:
            return request.render('vac_social_marketing.social_not_found')

        lead_vals      = {}
        custom_answers = {}

        for field in rec.registration_field_ids:
            post_key = f'custom_{field.id}'

            if field.field_type == 'checkbox':
                raw   = request.httprequest.form.get(post_key, '')
                value = '1' if raw else '0'
            else:
                value = request.httprequest.form.get(post_key, '').strip()

            if field.is_required and not value:
                _logger.warning(
                    f"Required field missing: id={field.id} label={field.label!r}"
                )
                return request.redirect(
                    f'/social/{platform}/invite/{slug}?error=missing_fields'
                )

            route_registration_value(
                request.env,
                field,
                value,
                lead_vals,
                custom_answers,
            )

        finalize_lead_values(lead_vals)

        if not lead_vals.get('name'):
            _logger.warning("No field mapped to Lead -> Full Name")
            return request.redirect(
                f'/social/{platform}/invite/{slug}?error=missing_fields'
            )

        try:
            lead_model   = request.env['vac.event.lead'].sudo()
            model_fields = lead_model._fields

            safe_vals = {
                k: v for k, v in lead_vals.items()
                if k in ('branch_service_id',) or k in model_fields
            }

            if 'platform' in model_fields:
                lead_platform = _PLATFORM_LEAD_VALUE.get(platform)
                if lead_platform:
                    safe_vals['platform'] = lead_platform
                    _logger.info(
                        f"[social_submit] platform set to '{lead_platform}' "
                        f"for URL platform='{platform}'"
                    )

            # Link the lead back to its source social campaign
            if platform == 'fb' and 'social_fb_id' in model_fields:
                safe_vals['social_fb_id'] = rec.id
            elif platform == 'ing' and 'social_ig_id' in model_fields:
                safe_vals['social_ig_id'] = rec.id
            elif platform == 'office' and 'social_office_id' in model_fields:
                safe_vals['social_office_id'] = rec.id

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

            # Default social_stage_id → first stage by sequence (dynamically created)
            if 'social_stage_id' in model_fields and 'social_stage_id' not in safe_vals:
                social_stage = request.env['vac.social.lead.stage'].sudo().search(
                    [], order='sequence, name', limit=1)
                if social_stage:
                    safe_vals['social_stage_id'] = social_stage.id

            lead = lead_model.create(safe_vals)
            _logger.info(f"Social lead created: {lead.name} ID={lead.id}")

            self._send_social_registration_email(lead, rec, platform, custom_answers)

            return request.redirect(
                f'/social/register/success'
                f'?platform={platform}&slug={slug}&lead_id={lead.id}'
            )

        except Exception as e:
            _logger.error(f"Social lead creation error: {e}", exc_info=True)
            return request.redirect(
                f'/social/{platform}/invite/{slug}?error=registration_failed'
            )

    # ─────────────────────────────────────────────────────────────────
    #  Confirmation e-mail
    # ─────────────────────────────────────────────────────────────────
    def _send_social_registration_email(self, lead, record, platform, custom_answers=None):
        from datetime import datetime

        # ── Dynamic sender: reads from Odoo settings, not hardcoded ──────────
        SENDER = self._get_sender_email()

        platform_label = _PLATFORM_LABELS.get(platform, platform)
        platform_sub = {
            'fb': 'Facebook Registration',
            'ing': 'Instagram Registration',
            'office': 'Offices Registration',
        }.get(platform, 'Social Registration')
        if platform == 'fb':
            platform_icon = (
                '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAACq0lEQVR4nO2dS3LCMBBEjSvbsIaTwhHCScMaDkBWECMsW5+Z6bHUb5vCn35qyTiUvRs2wOF0e5R87nrZ76SPRRp3B1gadirepLg4GO3QY3iQATsAVOgxUDLMd+ot+BBrEWY78x58iJUI9Z1sLfgQbRFqG9968CFaIkaNjbYW/jDonZO4gBbDf6JxbmK1ajn4OaSmJJGNeA//9+c7+rfj+V68XQkJ1RvwHP5S8CGlImolVH3Ya/g5wYeUiKiRULwItxh+6edrsigy5yH82qDXsGpCdgM8hO+VkmyyBPQUfmnDcjNKFtBT+LXkZKVyK4KkkySAoz+f1MxWBfQafs035Ccp2S0K6DV8SdYy5Bowg8ToTyUqoNfRrxH+UpZf4nvbKJajfspsA3oa/cfz3ST8WKZdNAA1ulP4aEBPo9+auWx5FQTmTQBHvz5hxmwAGAoA8xLA6ceOadZsABgKADMOA6cfBM/M2QAwFACGAsBQAJiRCzCOw+n2YAPAUAAYCgCzs14DtH/VnIqX/5KxAWAoAAwFgKEAMBQAhgLAUAAYCgBDAWBGDw+u65XrZb8z/3Gu1C0Ai+dAWMApCAwFgKEAMOMw+HiCbG88M2cDwFAAmJcATkN2TLNmA8BQAJg3AZyG9AkzZgPAfAhgC/SYy5YNADMrgC2QJ5YpGwAmKoAtkGMpSzYAzKIAtqCetQxXG0AJ5aRklzQFUUI+qZlxDQCTLIAtSCcnq6wGUMI6uRllT0GUEMfkBQ6lO2qd0kyKF2FK+Kcmi6ZfY2VB7UCsvgztuQkS5y7yPaBHCa5eZTil9SlJerCJfxNuuQ0a56ZyK6JFCVrnxFear7DZV5qHbE2EVYvNpwrvIqynT9hc7U0Eat1ysViiZHi4WIAfQIi2DA+hT3F1MDFKpXgLe44/J54G02TC0lQAAAAASUVORK5CYII=" '
                'width="52" height="52" alt="Facebook" '
                'style="display:inline-block;margin-bottom:10px;border-radius:50%;" />'
            )
        elif platform == 'ing':
            platform_icon = (
                '<img src="data:image/png;base64,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" '
                'width="52" height="52" alt="Instagram" '
                'style="display:inline-block;margin-bottom:10px;border-radius:14px;" />'
            )
        else:
            # Offices (and any other future platform) — generic building glyph.
            platform_icon = (
                '<div style="display:inline-flex;align-items:center;justify-content:center;'
                'width:52px;height:52px;border-radius:14px;background:rgba(255,255,255,0.18);'
                'margin-bottom:10px;font-size:26px;line-height:52px;">&#127970;</div>'
            )
        accent = _PLATFORM_ACCENTS.get(platform, '#714B67')
        try:
            def row(label, value, is_badge=False):
                if value in (None, '', False):
                    return ''
                badge_html = (
                    '<span style="display:inline-block;background:#e8f5e9;'
                    'color:#2e7d32;padding:3px 10px;border-radius:20px;'
                    f'font-size:13px;font-weight:600;">{value}</span>'
                ) if is_badge else f'<span style="font-size:14px;color:#333;">{value}</span>'
                return (
                    '<tr>'
                    '<td style="padding:11px 18px;border-bottom:1px solid #f0f0f0;'
                    'background:#fafafa;width:38%;vertical-align:top;">'
                    f'<span style="font-size:11px;font-weight:700;letter-spacing:.5px;'
                    f'text-transform:uppercase;color:#888;">{label}</span></td>'
                    f'<td style="padding:11px 18px;border-bottom:1px solid #f0f0f0;'
                    f'vertical-align:top;">{badge_html}</td>'
                    '</tr>'
                )

            def bool_row(label, flag):
                return row(label, 'Yes', is_badge=True) if flag else ''

            branch_service_name = lead.branch_service_id.name if lead.branch_service_id else ''
            va_rating = (str(int(lead.current_va_disability_rating)) + '%') if lead.current_va_disability_rating else ''
            email_link = (
                f'<a href="mailto:{lead.email}" style="color:{accent};font-weight:600;text-decoration:none;">{lead.email}</a>'
            ) if lead.email else ''

            birthday_str = lead.birthday.strftime('%B %d, %Y') if lead.birthday else ''
            notes_val    = getattr(lead, 'notes', '') or ''

            rows = (
                row('Full Name',            lead.name)
              + row('Email Address',        email_link)
              + row('Mobile / Phone',       getattr(lead, 'mobile', '') or '')
              + row('WhatsApp Number',      getattr(lead, 'whatsapp_number', '') or '')
              + row('Date of Birth',        birthday_str)
              + row('Branch / Service',     branch_service_name)
              + row('VA Disability Rating', va_rating)
              + bool_row('US Veteran',      lead.is_veteran)
              + bool_row('Has DD214 Access', lead.has_dd214_copy or lead.has_dd214_access)
              + bool_row('Current VAC Client', lead.is_current_client)
              + bool_row('Bringing a Plus One', lead.is_bringing_plus_one)
              + row('Physical Address',     getattr(lead, 'physical_address', '') or '')
              + row('Notes',               notes_val)
              + row('Campaign',             record.title)
              + row('Platform',             platform_label)
            )

            for data in (custom_answers or {}).values():
                val = data.get('value', '')
                if data.get('type') == 'checkbox':
                    if val == '1' and data.get('label'):
                        rows += row(data['label'], 'Yes', is_badge=True)
                elif data.get('label') and val:
                    rows += row(data['label'], val)

            body_html = (
                '<div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;'
                'background:#ffffff;border-radius:12px;overflow:hidden;'
                'box-shadow:0 4px 24px rgba(0,0,0,0.10);">'
                f'<div style="background:linear-gradient(135deg,#002855 0%,{accent} 100%);'
                'padding:36px 32px;text-align:center;">'
                f'{platform_icon}<br/>'
                '<span style="color:#ffffff;font-size:22px;font-weight:800;'
                'letter-spacing:0.5px;display:block;margin-bottom:4px;">'
                'Veterans Advocate Center</span>'
                f'<span style="color:rgba(255,255,255,0.75);font-size:11px;'
                'letter-spacing:3px;text-transform:uppercase;font-weight:500;">'
                f'{platform_sub}</span></div>'
                '<div style="text-align:center;padding:28px 32px 4px;">'
                '<span style="display:inline-block;background:#003366;color:#ffffff;'
                'padding:11px 32px;border-radius:50px;font-size:13px;font-weight:700;'
                'letter-spacing:2px;text-transform:uppercase;">'
                '&#10004;&nbsp;&nbsp;Registration Confirmed</span></div>'
                '<div style="padding:22px 32px 30px;">'
                f'<h2 style="color:#002855;margin:0 0 8px;font-size:22px;font-weight:700;">'
                f'Thank You, {lead.name}!</h2>'
                f'<p style="font-size:15px;line-height:1.75;color:#555;margin:0 0 24px;">'
                'We have successfully received your registration for '
                f'<strong style="color:#002855;">{record.title}</strong> '
                f'via <strong style="color:{accent};">{platform_label}</strong>. '
                'Our team will review your information and reach out to you shortly.</p>'
                '<div style="border:1px solid #e8edf3;border-radius:10px;overflow:hidden;margin-bottom:24px;">'
                f'<div style="background:linear-gradient(90deg,#002855,{accent});padding:12px 18px;">'
                '<span style="font-size:11px;font-weight:700;letter-spacing:2px;'
                'color:#ffffff;text-transform:uppercase;">&#128203;&nbsp;Submission Details</span></div>'
                f'<table style="width:100%;border-collapse:collapse;background:#fff;">{rows}</table></div>'
                '<p style="font-size:14px;line-height:1.75;color:#666;margin:0 0 6px;">'
                "If you have any questions or need immediate assistance, please don't hesitate to contact us.</p>"
                '<p style="font-size:15px;line-height:1.75;color:#333;margin:0;">'
                '<strong>Best regards,</strong><br/>'
                '<span style="color:#002855;font-weight:600;">Veterans Advocate Center Team</span></p></div>'
                '<div style="background:#002855;padding:24px 20px;text-align:center;">'
                '<p style="color:#ffffff;margin:0 0 4px;font-size:15px;font-weight:700;">'
                '&#127824; Veterans Advocate Center</p>'
                '<p style="color:rgba(255,255,255,0.65);margin:0 0 12px;font-size:13px;">'
                'Serving those who served us</p>'
                f'<p style="color:rgba(255,255,255,0.5);margin:0;font-size:11px;">'
                f'&copy; {datetime.now().year} Veterans Advocate Center. All rights reserved.'
                '&nbsp;|&nbsp;<a href="https://veteransadvocatecenter.com/" '
                'style="color:rgba(255,255,255,0.8);text-decoration:none;">Visit Our Website</a></p>'
                '</div></div>'
            )

            mail_vals = {
                'subject':     f'Registration Confirmed - {record.title} ({platform_label})',
                'body_html':   body_html,
                'email_to':    lead.email,
                'auto_delete': True,
            }
            if SENDER:
                mail_vals['email_from'] = SENDER

            # Capture everything needed before spawning the thread.
            # We do NOT rely on a mail.mail DB record because the HTTP
            # transaction may not be committed yet when the thread runs.
            # Instead we create + send inside the thread's own cursor.
            dbname     = request.env.cr.dbname
            _mail_vals = dict(mail_vals)   # snapshot – no ORM objects

            def _send_bg():
                try:
                    import odoo
                    with odoo.registry(dbname).cursor() as cr:
                        env2 = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                        mail = env2['mail.mail'].create(_mail_vals)
                        mail.send()
                except Exception as exc:
                    _logger.error(f"[social bg-mail] send failed: {exc}", exc_info=True)

            threading.Thread(target=_send_bg, daemon=True).start()

        except Exception as e:
            _logger.error(f"Social email error: {e}", exc_info=True)

    # ─────────────────────────────────────────────────────────────────
    #  Success page  (GET)
    # ─────────────────────────────────────────────────────────────────
    @http.route(
        '/social/register/success',
        type='http', auth='public', website=True,
    )
    def social_registration_success(self, **kwargs):
        try:
            platform = kwargs.get('platform', '')
            slug     = kwargs.get('slug', '')
            lead_id  = int(kwargs.get('lead_id', 0))
        except (ValueError, TypeError):
            return request.render('vac_social_marketing.social_not_found')

        rec  = self._get_social_record_by_slug(platform, slug)
        lead = request.env['vac.event.lead'].sudo().browse(lead_id)

        if not rec or not lead.exists():
            return request.render('vac_social_marketing.social_not_found')

        custom_answers = {}
        if lead.custom_field_answers:
            try:
                custom_answers = json.loads(lead.custom_field_answers)
            except Exception:
                custom_answers = {}

        platform_label = _PLATFORM_LABELS.get(platform, platform)
        return request.render('vac_social_marketing.social_registration_success', {
            'record':          rec,
            'lead':            lead,
            'platform':        platform,
            'platform_label':  platform_label,
            'custom_answers':  custom_answers,
        })