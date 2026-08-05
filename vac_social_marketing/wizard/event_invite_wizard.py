# -*- coding: utf-8 -*-
from odoo import models, fields, api


def _build_share_html(event):
    """
    Build the share-dialog HTML block:
      - QR code (via Odoo image URL, no embedded base64)
      - Styled registration link
    Copy and Print are handled by footer buttons + server actions.
    """
    if not event:
        return '<p style="color:#9ca3af;text-align:center;padding:20px;">No event selected.</p>'

    link = event.event_link or ''
    qr_url = f'/web/image/vac.event/{event.id}/qr_code'
    has_qr = bool(event.qr_code)

    qr_block = ''
    if has_qr:
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
                QR code will appear once the event link is generated.
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
            No registration link yet — save the event first.
        </div>'''

    return f'''
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
            padding:8px 4px;">
    {qr_block}
    {link_block}
</div>'''


class VacEventInviteWizard(models.TransientModel):
    _name = 'vac.event.invite.wizard'
    _description = 'Share Event Link Wizard'

    event_id = fields.Many2one(
        'vac.event', string='Event', required=True, readonly=True
    )
    event_link = fields.Char(
        string='Registration Link',
        related='event_id.event_link',
        readonly=True,
    )
    share_html = fields.Html(
        string='Share',
        compute='_compute_share_html',
        sanitize=False,
    )

    @api.depends('event_id', 'event_id.qr_code', 'event_id.event_link')
    def _compute_share_html(self):
        for wizard in self:
            wizard.share_html = _build_share_html(wizard.event_id)

    def action_copy_link(self):
        """Copy the registration link to the browser clipboard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'vac_social_marketing.copy_registration_link',
            'params': {
                'link': self.event_link or '',
            },
        }

    def action_print_qr(self):
        """Open a print-ready QR page in a new tab.
        The page auto-triggers the browser's Print dialog so the user
        can choose 'Save as PDF' or send to a printer.
        """
        self.ensure_one()
        if not self.event_id or not self.event_id.qr_code:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No QR Code',
                    'message': 'QR code is not available for this event yet.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.act_url',
            'url': f'/event/print-qr/{self.event_id.id}',
            'target': 'new',
        }
