# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import html_escape
from jinja2.sandbox import SandboxedEnvironment
from urllib.parse import quote
from types import SimpleNamespace


class VacMailTemplateConfig(models.Model):
    _name = 'vac.mail.template.config'
    _description = 'VAC Email Template Builder'
    _rec_name = 'name'

    name = fields.Char(string='Template Name', required=True)

    # ── HEADER ──────────────────────────────────────────────────────────────

    header_logo = fields.Binary(
        string='Header Logo',
        attachment=True,
        help='Logo displayed at the top of the email header',
    )
    header_logo_filename = fields.Char()

    header_bg_color = fields.Char(
        string='Header Background Color',
        default='#1a3a5c',
        help='Hex background color for the header (e.g. #1a3a5c)',
    )
    header_bg_image = fields.Binary(
        string='Header Background Image',
        attachment=True,
        help='Optional background image for the header — overrides the background color',
    )
    header_bg_image_filename = fields.Char()

    header_title = fields.Char(
        string='Header Title',
        default='Veterans Advocate Center',
        help='Main heading text shown in the header',
    )
    header_subtitle = fields.Char(
        string='Header Subtitle',
        default='Event Registration Confirmation',
        help='Smaller text below the title',
    )
    header_text_color = fields.Char(
        string='Header Text Color',
        default='#ffffff',
    )

    # ── BODY / MIDDLE ────────────────────────────────────────────────────────

    body_html = fields.Html(
        string='Body Content',
        sanitize=False,
        help=(
            'Main email body — supports rich text and Jinja2 placeholders:\n'
            '  {{ object.name }}               → registrant full name\n'
            '  {{ object.email }}              → registrant email\n'
            '  {{ object.event_id.title_name }} → event title\n'
            '  {{ object.event_id.date }}       → event date\n'
            '  {{ object.event_id.venue }}      → event venue'
        ),
    )

    body_show_reg_details = fields.Boolean(
        string='Show Registration Details Table',
        default=False,
        help='Append the full registration details table below the body content',
    )

    body_bg_image = fields.Binary(
        string='Body Background Image',
        attachment=True,
        help='Watermark/background image shown behind the body text (e.g. eagle, military image)',
    )
    body_bg_image_filename = fields.Char()

    body_bg_overlay = fields.Float(
        string='White Overlay Opacity',
        default=0.88,
        digits=(3, 2),
        help=(
            'Controls how faded/whitish the background image appears.\n'
            '0.0 = image fully visible  |  1.0 = completely white (image hidden)\n'
            'Recommended: 0.80 – 0.92 for a soft watermark look'
        ),
    )

    # ── FOOTER ──────────────────────────────────────────────────────────────

    footer_logo = fields.Binary(
        string='Footer Logo',
        attachment=True,
    )
    footer_logo_filename = fields.Char()
    footer_full_image = fields.Binary(
        string='Full Footer Image',
        attachment=True,
        help='Upload a complete footer design. When set, only this image is shown in the footer.',
    )
    footer_full_image_filename = fields.Char()

    footer_bg_color = fields.Char(
        string='Footer Background Color',
        default='#1a3a5c',
    )
    footer_text_color = fields.Char(
        string='Footer Text Color',
        default='#ffffff',
    )
    footer_tagline = fields.Char(
        string='Footer Tagline',
        default='YOU SERVED, YOU DESERVE',
    )
    footer_message = fields.Char(
        string='Footer Message',
        default='The right knowledge can change your claim journey.',
    )
    footer_accent_color = fields.Char(
        string='Footer Accent Color',
        default='#f7c847',
    )
    footer_phone = fields.Char(string='Phone')
    footer_email = fields.Char(string='Contact Email')
    footer_website = fields.Char(string='Website')

    footer_show_buttons = fields.Boolean(string='Show Footer Buttons', default=True)
    footer_btn1_label = fields.Char(string='Button 1 Label', default='LEARN MORE')
    footer_btn1_url   = fields.Char(string='Button 1 URL',   default='https://veteransadvocatecenter.com')
    footer_btn1_bg_color = fields.Char(string='Button 1 Background', default='#b82d21')
    footer_btn1_text_color = fields.Char(string='Button 1 Text Color', default='#000000')
    footer_btn1_border_color = fields.Char(string='Button 1 Border Color', default='#d7ad45')
    footer_btn2_label = fields.Char(string='Button 2 Label', default='CONTACT US')
    footer_btn2_url   = fields.Char(string='Button 2 URL',   default='https://veteransadvocatecenter.com/contact')
    footer_btn2_bg_color = fields.Char(string='Button 2 Background', default='#ffffff')
    footer_btn2_text_color = fields.Char(string='Button 2 Text Color', default='#111111')
    footer_btn2_border_color = fields.Char(string='Button 2 Border Color', default='#d7ad45')
    footer_button_ids = fields.One2many(
        'vac.mail.template.button',
        'template_id',
        string='Footer Buttons',
    )

    preview_html = fields.Html(
        string='Live Preview',
        compute='_compute_preview_html',
        sanitize=False,
    )

    # ── HELPERS ──────────────────────────────────────────────────────────────

    def _img_tag(self, field_name, alt='', style='', preview=False):
        """Return an email-safe image tag for an uploaded template image."""
        if not self[field_name]:
            return ''
        return (
            f'<img src="{self._image_src(field_name, preview=preview)}" alt="{html_escape(alt)}" '
            f'style="{style}display:block;margin:0 auto;"/>'
        )

    def _base_url(self):
        icp = self.env['ir.config_parameter'].sudo()
        url = (
            icp.get_param('web.base.url.freeze')
            or icp.get_param('web.base.url')
            or ''
        ).rstrip('/')
        return url

    def _image_url(self, field_name):
        filename = self[f'{field_name}_filename'] or f'{field_name}.png'
        return (
            f'{self._base_url()}/vac/email-template/{self.id}/'
            f'{field_name}/{quote(filename)}'
        )

    def _image_src(self, field_name, preview=False):
        """Embed images as base64 so they always render in email clients."""
        if not self[field_name]:
            return ''
        if preview and isinstance(self.id, int):
            filename = self[f'{field_name}_filename'] or f'{field_name}.png'
            return f'/web/image/{self._name}/{self.id}/{field_name}/{quote(filename)}'
        # For sent emails and unsaved previews: embed as inline base64
        image_data = self[field_name]
        if isinstance(image_data, bytes):
            image_data = image_data.decode()
        filename = (self[f'{field_name}_filename'] or '').lower()
        if filename.endswith(('.jpg', '.jpeg')):
            mime = 'image/jpeg'
        elif filename.endswith('.gif'):
            mime = 'image/gif'
        elif filename.endswith('.webp'):
            mime = 'image/webp'
        elif filename.endswith('.svg'):
            mime = 'image/svg+xml'
        else:
            mime = 'image/png'
        return f'data:{mime};base64,{image_data}'

    # ── TEMPLATE BUILDER ────────────────────────────────────────────────────

    def _build_full_template_html(self, preview=False):
        """
        Assemble the complete email HTML (with Jinja2 placeholders intact)
        from the three sections: header, body, footer.
        """
        self.ensure_one()

        # ── HEADER background ──
        if self.header_bg_image:
            hdr_bg = (
                f'background-image:url({self._image_src("header_bg_image", preview=preview)});'
                f'background-size:cover;background-position:center;'
            )
        else:
            hdr_bg = f'background:{self.header_bg_color or "#1a3a5c"};'

        logo_html = self._img_tag(
            'header_logo', 'Logo',
            'max-height:78px;max-width:190px;',
            preview=preview,
        )

        # ── FOOTER logo ──
        footer_logo_html = self._img_tag(
            'footer_logo', 'Logo',
            'width:104px;height:104px;max-width:104px;max-height:104px;object-fit:cover;border-radius:50%;',
            preview=preview,
        )

        # ── CONTACT strip rows ──
        fc = self.footer_text_color or '#ffffff'
        contact_rows = []
        if self.footer_phone:
            contact_rows.append(
                f'<tr><td style="width:26px;padding:4px 8px 4px 0;">'
                f'<span style="display:inline-block;width:19px;height:19px;border:1px solid #d7ad45;'
                f'border-radius:50%;line-height:19px;text-align:center;color:#d7ad45;font-size:11px;">&#9742;</span>'
                f'</td><td style="padding:4px 0;font-size:10px;color:#111827;">'
                f'<strong>Phone:</strong>&nbsp; {self.footer_phone}</td></tr>'
            )
        if self.footer_email:
            contact_rows.append(
                f'<tr><td style="width:26px;padding:4px 8px 4px 0;">'
                f'<span style="display:inline-block;width:19px;height:19px;border:1px solid #d7ad45;'
                f'border-radius:50%;line-height:19px;text-align:center;color:#d7ad45;font-size:11px;">@</span>'
                f'</td><td style="padding:4px 0;font-size:10px;color:#111827;">'
                f'<strong>Email:</strong>&nbsp; <a href="mailto:{self.footer_email}" '
                f'style="color:#111827;text-decoration:none;">{self.footer_email}</a></td></tr>'
            )
        if self.footer_website:
            site = (self.footer_website or '').strip()
            if site.startswith('https://'):
                site = site[8:]
            elif site.startswith('http://'):
                site = site[7:]
            contact_rows.append(
                f'<tr><td style="width:26px;padding:4px 8px 4px 0;">'
                f'<span style="display:inline-block;width:19px;height:19px;border:1px solid #d7ad45;'
                f'border-radius:50%;line-height:19px;text-align:center;color:#d7ad45;font-size:11px;">&#9678;</span>'
                f'</td><td style="padding:4px 0;font-size:10px;color:#111827;">'
                f'<strong>Website:</strong>&nbsp; <a href="https://{site}" '
                f'style="color:#111827;text-decoration:none;">{self.footer_website}</a></td></tr>'
            )
        contact_rows_html = ''.join(contact_rows)

        # ── FOOTER buttons ──
        btns_html = ''
        if self.footer_show_buttons:
            btns = []
            button_rows = self.footer_button_ids.sorted('sequence')
            if button_rows:
                for button in button_rows:
                    if button.label and button.url:
                        btns.append(
                            f'<td style="padding:0 8px 0 0;vertical-align:top;white-space:nowrap;">'
                            f'<a href="{html_escape(button.url)}" '
                            f'style="display:block;background-color:{button.bg_color or "#ffffff"};'
                            f'color:{button.text_color or "#111111"};'
                            f'padding:8px 28px;border-radius:4px;font-weight:800;'
                            f'font-size:12px;line-height:16px;text-decoration:none;text-align:center;display:block;'
                            f'border:1px solid {button.border_color or "#d7ad45"};">'
                            f'<span style="text-decoration:none;">{html_escape(button.label)}</span></a></td>'
                        )
            else:
                if self.footer_btn1_label and self.footer_btn1_url:
                    btns.append(
                        f'<td style="padding:0 8px 0 0;vertical-align:top;white-space:nowrap;">'
                        f'<a href="{html_escape(self.footer_btn1_url)}" '
                        f'style="display:block;background-color:{self.footer_btn1_bg_color or "#b82d21"};'
                        f'color:{self.footer_btn1_text_color or "#000000"};'
                        f'padding:8px 28px;border-radius:4px;font-weight:800;'
                        f'font-size:12px;line-height:16px;text-decoration:none;text-align:center;display:block;'
                        f'border:1px solid {self.footer_btn1_border_color or "#d7ad45"};">'
                        f'<span style="text-decoration:none;">{html_escape(self.footer_btn1_label)}</span></a></td>'
                    )
                if self.footer_btn2_label and self.footer_btn2_url:
                    btns.append(
                        f'<td style="padding:0 8px 0 0;vertical-align:top;white-space:nowrap;">'
                        f'<a href="{html_escape(self.footer_btn2_url)}" '
                        f'style="display:block;background-color:{self.footer_btn2_bg_color or "#ffffff"};'
                        f'color:{self.footer_btn2_text_color or "#111111"};'
                        f'padding:8px 28px;border-radius:4px;font-weight:800;'
                        f'font-size:12px;line-height:16px;text-decoration:none;text-align:center;display:block;'
                        f'border:1px solid {self.footer_btn2_border_color or "#d7ad45"};">'
                        f'<span style="text-decoration:none;">{html_escape(self.footer_btn2_label)}</span></a></td>'
                    )
            if btns:
                button_rows_html = ''.join(
                    f'<tr>{"".join(btns[index:index + 3])}</tr>'
                    for index in range(0, len(btns), 3)
                )
                btns_html = (
                    '<table role="presentation" style="border-collapse:collapse;margin-top:14px;">'
                    f'{button_rows_html}</table>'
                )

        body_content = self.body_html or ''

        title     = (self.header_title or '').upper()
        title_parts = title.split()
        if len(title_parts) >= 3:
            title_html = (
                f'<span style="color:#e21d2f;">{title_parts[0]}</span><br/>'
                f'<span style="color:#ffffff;">{title_parts[1]}</span><br/>'
                f'<span style="color:#3b91d9;">{" ".join(title_parts[2:])}</span>'
            )
        else:
            title_html = f'<span style="color:{self.header_text_color or "#ffffff"};">{title}</span>'
        subtitle  = self.header_subtitle or ''
        txt_color = self.header_text_color or '#ffffff'
        ftbg      = self.footer_bg_color  or '#1a3a5c'
        accent    = self.footer_accent_color or '#f7c847'
        tagline   = self.footer_tagline   or ''
        footer_message = self.footer_message or ''
        if self.footer_full_image:
            footer_section = f"""
    <div style="background:{ftbg};">
        <img src="{self._image_src("footer_full_image", preview=preview)}" alt="Footer"
             style="display:block;width:100%;max-width:620px;height:auto;border:0;"/>
    </div>"""
        else:
            footer_section = f"""
    <div style="background:rgba(255,255,255,0.82);border-top:2px solid #d8b75a;
                padding:10px 36px 10px;">
        <table role="presentation" style="border-collapse:collapse;">
            {contact_rows_html}
        </table>
    </div>
    <div style="background:{ftbg};padding:13px 34px 16px;">
        <table role="presentation" style="width:100%;border-collapse:collapse;">
            <tr>
                <td colspan="2" style="text-align:center;padding-bottom:10px;border-bottom:2px solid {accent};">
                    <span style="color:{accent};font-size:18px;letter-spacing:7px;">&#9733; &#9733; &#9733;</span>
                    <span style="color:{accent};font-size:15px;font-weight:900;text-transform:uppercase;
                                 letter-spacing:2px;padding:0 14px;">{tagline}</span>
                    <span style="color:{accent};font-size:18px;letter-spacing:7px;">&#9733; &#9733; &#9733;</span>
                </td>
            </tr>
            <tr>
                <td style="width:124px;vertical-align:middle;text-align:left;padding-top:10px;">{footer_logo_html}</td>
                <td style="vertical-align:top;text-align:left;padding-left:18px;padding-top:10px;">
                    <div style="color:{accent};font-size:14px;font-weight:800;line-height:1.25;
                                margin-bottom:4px;">{footer_message}</div>
                    {btns_html}
                </td>
            </tr>
        </table>
    </div>"""
        if self.header_bg_image:
            header_content = ''
        else:
            header_content = f"""
        <table role="presentation" style="width:100%;height:96px;border-collapse:collapse;">
            <tr>
                <td style="width:116px;vertical-align:middle;">{logo_html}</td>
                <td style="vertical-align:middle;padding-left:8px;">
                    <div style="font-size:26px;font-weight:900;line-height:0.86;letter-spacing:1px;">
                        {title_html}
                    </div>
                    <div style="color:{txt_color};font-size:9px;font-weight:700;letter-spacing:0.8px;
                                margin-top:2px;text-transform:uppercase;">{subtitle}</div>
                </td>
                <td style="width:170px;vertical-align:middle;text-align:right;color:#d7ad45;
                           font-size:17px;font-weight:700;letter-spacing:4px;">
                    <span style="letter-spacing:0;color:#d7ad45;">&mdash;</span>
                    &#9733;&#9733;&#9733;&#9733;&#9733;
                    <span style="letter-spacing:0;color:#d7ad45;">&mdash;</span>
                </td>
            </tr>
        </table>"""

        # ── BODY background image with white overlay ──
        overlay   = max(0.0, min(1.0, self.body_bg_overlay or 0.88))
        if self.body_bg_image:
            body_outer_style = (
                f'background-image:url({self._image_src("body_bg_image", preview=preview)});'
                f'background-size:cover;background-position:center center;background-repeat:no-repeat;'
            )
            body_inner_style = (
                f'background:rgba(255,255,255,{overlay:.2f});'
                f'padding:54px 34px;min-height:560px;'
            )
            body_section = f"""
    <div style="{body_outer_style}border-top:1px solid #d8b75a;">
        <div style="{body_inner_style}">
            {body_content}
        </div>
    </div>"""
        else:
            body_section = f"""
    <div style="padding:54px 34px;background:#ffffff;border-top:1px solid #d8b75a;min-height:560px;">
        {body_content}
    </div>"""

        return f"""
<div style="font-family:Arial,Helvetica,sans-serif;max-width:620px;margin:0 auto;
            background:#ffffff;border:1px solid #c9c9c9;overflow:hidden;">
    <div style="{hdr_bg}height:96px;padding:0 18px;">
{header_content}
    </div>
{body_section}
{footer_section}
</div>
"""

    @api.depends(
        'header_logo',
        'header_logo_filename',
        'header_bg_color',
        'header_bg_image',
        'header_bg_image_filename',
        'header_title',
        'header_subtitle',
        'header_text_color',
        'body_html',
        'body_show_reg_details',
        'body_bg_image',
        'body_bg_image_filename',
        'body_bg_overlay',
        'footer_logo',
        'footer_logo_filename',
        'footer_full_image',
        'footer_full_image_filename',
        'footer_bg_color',
        'footer_text_color',
        'footer_accent_color',
        'footer_tagline',
        'footer_message',
        'footer_phone',
        'footer_email',
        'footer_website',
        'footer_show_buttons',
        'footer_btn1_label',
        'footer_btn1_url',
        'footer_btn1_bg_color',
        'footer_btn1_text_color',
        'footer_btn1_border_color',
        'footer_btn2_label',
        'footer_btn2_url',
        'footer_btn2_bg_color',
        'footer_btn2_text_color',
        'footer_btn2_border_color',
        'footer_button_ids',
        'footer_button_ids.sequence',
        'footer_button_ids.label',
        'footer_button_ids.url',
        'footer_button_ids.bg_color',
        'footer_button_ids.text_color',
        'footer_button_ids.border_color',
    )
    def _compute_preview_html(self):
        preview_object = SimpleNamespace(
            name='John Veteran',
            email='john.veteran@example.com',
            mobile='+1 555-0100',
            event_id=SimpleNamespace(
                title_name='Veterans Benefits Webinar',
                date='May 20, 2026',
                venue='Online',
            ),
        )
        jinja_env = SandboxedEnvironment(autoescape=False)
        for template in self:
            raw_html = template._build_full_template_html(preview=True)
            try:
                template.preview_html = jinja_env.from_string(raw_html).render(
                    object=preview_object,
                    user=template.env.user,
                )
            except Exception:
                template.preview_html = raw_html

    # ── EMAIL SENDER ─────────────────────────────────────────────────────────

    def _get_image_cid_map(self):
        """
        Return a dict mapping field_name -> (cid, base64_data, mime_type)
        for each image field that has data. Used to send images as inline
        attachments (CID references) so email clients always display them.
        """
        image_fields = ['header_logo', 'header_bg_image', 'footer_logo', 'footer_full_image', 'body_bg_image']
        cid_map = {}
        for field_name in image_fields:
            if not self[field_name]:
                continue
            image_data = self[field_name]
            if isinstance(image_data, bytes):
                image_data = image_data.decode()
            filename = (self[f'{field_name}_filename'] or '').lower()
            if filename.endswith(('.jpg', '.jpeg')):
                mime = 'image/jpeg'
            elif filename.endswith('.gif'):
                mime = 'image/gif'
            elif filename.endswith('.webp'):
                mime = 'image/webp'
            elif filename.endswith('.svg'):
                mime = 'image/svg+xml'
            else:
                mime = 'image/png'
            cid = f'vac_img_{field_name}_{self.id}@email'
            cid_map[field_name] = (cid, image_data, mime)
        return cid_map

    def send_email(self, lead, event=None, sender_email=None, subject_title=None):
        """
        Build a proper multipart/related MIME email with inline CID images
        and send it directly via Odoo's outgoing mail server (ir.mail_server).
        This bypasses mail.mail sanitisation so images appear inline, not as
        attachments.

        `event` is kept for backward compatibility with vac.event callers and
        is used to derive the subject line when `subject_title` isn't passed
        explicitly. Other callers (e.g. BAM forms) can pass `subject_title`
        directly without needing a vac.event record.
        """
        import base64 as _base64
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage

        self.ensure_one()

        # 1. Build CID map
        cid_map = self._get_image_cid_map()

        # 2. Generate HTML (data: URIs) then swap each for its cid: reference
        raw_html = self._build_full_template_html(preview=False)
        for field_name, (cid, image_data, mime) in cid_map.items():
            data_uri = f'data:{mime};base64,{image_data}'
            raw_html = raw_html.replace(data_uri, f'cid:{cid}')

        # 3. Render Jinja2 placeholders
        try:
            jinja_env = SandboxedEnvironment(autoescape=False)
            rendered_html = jinja_env.from_string(raw_html).render(
                object=lead,
                user=self.env.user,
            )
        except Exception:
            rendered_html = raw_html

        # 4. Build MIME structure:
        #    multipart/mixed
        #      └─ multipart/related
        #           ├─ text/html  (the rendered body)
        #           └─ image/*   (one per inline image, Content-Disposition: inline)
        msg_mixed = MIMEMultipart('mixed')

        title = subject_title or (event.title_name if event else None) or lead.referral_name or ''
        subject = f'Registration Confirmed – {title}'
        from_addr = sender_email or 'noreply@veteransadvocatecenter.com'
        to_addr = lead.email or ''

        msg_mixed['Subject'] = subject
        msg_mixed['From']    = from_addr
        msg_mixed['To']      = to_addr

        msg_related = MIMEMultipart('related')
        msg_mixed.attach(msg_related)

        # HTML part
        html_part = MIMEText(rendered_html, 'html', 'utf-8')
        msg_related.attach(html_part)

        # Inline image parts
        for field_name, (cid, image_data_b64, mime_type) in cid_map.items():
            try:
                img_bytes = _base64.b64decode(image_data_b64)
                subtype = mime_type.split('/')[-1]  # e.g. 'png', 'jpeg'
                img_part = MIMEImage(img_bytes, _subtype=subtype)
                img_part.add_header('Content-ID', f'<{cid}>')
                img_part.add_header('Content-Disposition', 'inline',
                                    filename=self[f'{field_name}_filename'] or f'{field_name}.{subtype}')
                msg_related.attach(img_part)
            except Exception:
                pass

        # 5. Send via Odoo's configured outgoing mail server
        try:
            ir_mail_server = self.env['ir.mail_server'].sudo()
            ir_mail_server.send_email(msg_mixed)
        except Exception:
            # Fallback: queue via mail.mail without inline images
            mail_vals = {
                'subject'    : subject,
                'body_html'  : rendered_html,
                'email_to'   : to_addr,
                'auto_delete': True,
            }
            if sender_email:
                mail_vals['email_from'] = sender_email
            import threading
            dbname     = self.env.cr.dbname
            _mail_vals = dict(mail_vals)

            def _send_bg():
                try:
                    import odoo
                    with odoo.registry(dbname).cursor() as cr:
                        env2 = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                        mail = env2['mail.mail'].create(_mail_vals)
                        mail.send()
                except Exception as exc:
                    _logger.error(f"[template bg-mail] send failed: {exc}", exc_info=True)

            threading.Thread(target=_send_bg, daemon=True).start()


class VacMailTemplateButton(models.Model):
    _name = 'vac.mail.template.button'
    _description = 'VAC Email Template Footer Button'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'vac.mail.template.config',
        string='Email Template',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    label = fields.Char(string='Label', required=True, default='NEW BUTTON')
    url = fields.Char(string='URL', required=True, default='https://veteransadvocatecenter.com')
    bg_color = fields.Char(string='Background', default='#ffffff')
    text_color = fields.Char(string='Text Color', default='#111111')
    border_color = fields.Char(string='Border Color', default='#d7ad45')
