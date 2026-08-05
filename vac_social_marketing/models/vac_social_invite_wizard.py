# -*- coding: utf-8 -*-
from odoo import models, fields, api


def _build_social_share_html(link, qr_url, has_qr):
    """
    Build the share-dialog HTML block for a social campaign:
      - QR code (via Odoo image URL)
      - Styled registration link
    Copy and Print are handled by footer buttons.
    """
    qr_block = ''
    if has_qr and qr_url:
        qr_block = f'''
        <div style="text-align:center;margin-bottom:28px;">
            <div style="display:inline-block;padding:14px;background:#ffffff;
                        border:1px solid #e5e7eb;border-radius:12px;
                        box-shadow:0 2px 10px rgba(0,0,0,0.08);">
                <img src="{qr_url}"
                     style="width:190px;height:190px;display:block;"
                     alt="QR Code"/>
            </div>
            <p style="margin:10px 0 0;font-size:12px;color:#6b7280;font-style:italic;">
                Scan to open registration form
            </p>
        </div>'''
    else:
        qr_block = '''
        <div style="text-align:center;margin-bottom:24px;padding:24px;
                    background:#f9fafb;border:1px dashed #d1d5db;border-radius:10px;">
            <p style="color:#9ca3af;font-size:13px;margin:0;">
                QR code will appear once the campaign link is generated.
            </p>
        </div>'''

    link_block = ''
    if link:
        link_block = f'''
        <div style="margin-bottom:4px;">
            <span style="font-size:12px;font-weight:600;color:#374151;
                         text-transform:uppercase;letter-spacing:.5px;">
                Registration Link
            </span>
        </div>
        <div style="background:#f0f7ff;border:1px solid #bfdbfe;border-radius:8px;
                    padding:12px 16px;">
            <a href="{link}" target="_blank"
               style="color:#1d4ed8;font-size:13px;font-weight:500;
                      word-break:break-all;text-decoration:none;">
                {link}
            </a>
        </div>
        <p style="margin:8px 0 0;font-size:11px;color:#9ca3af;">
            Use the <strong>Copy Link</strong> button below to copy,
            or <strong>Print QR</strong> to get a printable QR sheet.
        </p>'''
    else:
        link_block = '''
        <div style="padding:12px;background:#fef9c3;border:1px solid #fde047;
                    border-radius:8px;font-size:13px;color:#854d0e;">
            No registration link yet — save the campaign first.
        </div>'''

    return f'''
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
            padding:8px 4px;">
    {qr_block}
    {link_block}
</div>'''


class VacSocialInviteWizard(models.TransientModel):
    _name = 'vac.social.invite.wizard'
    _description = 'Share Social Campaign Link Wizard'

    title = fields.Char(string='Campaign', readonly=True)

    social_link = fields.Char(
        string='Registration Link',
        readonly=True,
        help='Shareable campaign registration link',
    )

    # Source record info — needed to look up the QR code image
    source_model = fields.Char(string='Source Model', readonly=True)
    source_id = fields.Integer(string='Source Record ID', readonly=True)

    qr_image_url = fields.Char(
        string='QR Image URL',
        compute='_compute_qr_image_url',
    )

    share_html = fields.Html(
        string='Share',
        compute='_compute_share_html',
        sanitize=False,
    )

    @api.depends('source_model', 'source_id')
    def _compute_qr_image_url(self):
        for wizard in self:
            if wizard.source_model and wizard.source_id:
                wizard.qr_image_url = (
                    f'/web/image/{wizard.source_model}/{wizard.source_id}/qr_code'
                )
            else:
                wizard.qr_image_url = False

    @api.depends('social_link', 'source_model', 'source_id')
    def _compute_share_html(self):
        for wizard in self:
            has_qr = False
            if wizard.source_model and wizard.source_id:
                try:
                    record = self.env[wizard.source_model].sudo().browse(wizard.source_id)
                    has_qr = bool(record.exists() and record.qr_code)
                except Exception:
                    has_qr = False
            wizard.share_html = _build_social_share_html(
                wizard.social_link,
                wizard.qr_image_url,
                has_qr,
            )

    def action_copy_link(self):
        """Copy the registration link to the browser clipboard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'vac_social_marketing.copy_registration_link',
            'params': {
                'link': self.social_link or '',
            },
        }

    def action_print_qr(self):
        """Open a print-ready QR page in a new tab.
        The page auto-triggers the browser's Print dialog so the user
        can choose 'Save as PDF' or send to a printer.
        """
        self.ensure_one()
        if not self.qr_image_url or not self.source_model or not self.source_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No QR Code',
                    'message': 'QR code is not available for this campaign yet.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.act_url',
            'url': f'/social/print-qr/{self.source_model}/{self.source_id}',
            'target': 'new',
        }
