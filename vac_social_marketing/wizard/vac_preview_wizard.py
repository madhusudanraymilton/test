# -*- coding: utf-8 -*-
from odoo import models, fields, api


def _build_preview_html(url, title=''):
    """
    Build browser-chrome + iframe HTML entirely in Python so that no
    forbidden t-att-* / t-attf-* directives are needed in the XML arch.
    Odoo 18 backend views forbid all OWL template directives.
    """
    if not url:
        return ''
    safe_url = url.replace('"', '%22')
    safe_title = (title or '').replace('"', '&quot;')
    return f'''
<div style="width:100%;border:1px solid #dee2e6;border-radius:6px;overflow:hidden;background:#f8f9fa;font-family:Arial,sans-serif;">
  <!-- Browser chrome bar -->
  <div style="background:#e9ecef;padding:8px 12px;display:flex;align-items:center;gap:8px;border-bottom:1px solid #dee2e6;">
    <span style="width:12px;height:12px;border-radius:50%;background:#ff5f57;display:inline-block;flex-shrink:0;"></span>
    <span style="width:12px;height:12px;border-radius:50%;background:#febc2e;display:inline-block;flex-shrink:0;"></span>
    <span style="width:12px;height:12px;border-radius:50%;background:#28c840;display:inline-block;flex-shrink:0;"></span>
    <span style="flex:1;background:white;border-radius:4px;padding:3px 10px;font-size:12px;color:#6c757d;margin-left:6px;border:1px solid #ced4da;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">
      &#128274; {url}
    </span>
    <a href="{safe_url}" target="_blank"
       style="flex-shrink:0;font-size:11px;padding:3px 10px;border:1px solid #0d6efd;border-radius:4px;color:#0d6efd;text-decoration:none;background:white;white-space:nowrap;">
      &#8599; Open
    </a>
  </div>
  <!-- Live page iframe -->
  <iframe src="{safe_url}"
          title="{safe_title}"
          style="width:100%;height:780px;border:none;display:block;"
          loading="lazy"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups">
  </iframe>
</div>'''


class VacEventPreviewWizard(models.TransientModel):
    """
    Preview wizard for vac.event — embeds the live public registration
    page in an iframe so the admin sees exactly what a visitor sees.

    For unpublished events the iframe points to the backend-only preview
    route (/event/invite/<id>/preview, auth='user') so the full
    registration form is always visible regardless of publish state.
    Once the event is published the same URL is used (it still works).
    """
    _name = 'vac.event.preview.wizard'
    _description = 'Event Preview Wizard'

    event_id = fields.Many2one(
        'vac.event',
        string='Event',
        required=True,
        readonly=True,
    )
    title_name = fields.Char(
        string='Event Title',
        related='event_id.title_name',
        readonly=True,
    )
    event_link = fields.Char(
        string='Event Link',
        related='event_id.event_link',
        readonly=True,
    )
    published = fields.Boolean(
        string='Currently Published',
        related='event_id.published',
        readonly=True,
    )
    preview_url = fields.Char(
        string='Preview URL',
        compute='_compute_preview_url',
    )
    preview_html = fields.Html(
        string='Live Preview',
        compute='_compute_preview_html',
        sanitize=False,
    )

    @api.depends('event_id')
    def _compute_preview_url(self):
        """
        Always build a URL to the backend-only preview route so the
        iframe shows the full registration form even when the event is
        not yet published.  The route (/event/invite/<id>/preview) uses
        auth='user', so the session cookie of the logged-in backend user
        is enough — no extra token is required.
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for wizard in self:
            if wizard.event_id:
                wizard.preview_url = f"{base_url}/event/invite/{wizard.event_id.id}/preview"
            else:
                wizard.preview_url = False

    @api.depends('preview_url', 'title_name')
    def _compute_preview_html(self):
        for wizard in self:
            wizard.preview_html = _build_preview_html(
                wizard.preview_url, wizard.title_name)

    def action_publish_now(self):
        """Publish the event directly from the preview wizard."""
        self.ensure_one()
        stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Published')], limit=1)
        vals = {'published': True}
        if stage:
            vals['stage_id'] = stage.id
        self.event_id.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Event Published!',
                'message': f'"{self.event_id.title_name}" is now live.',
                'type': 'success',
                'sticky': False,
            },
        }


class VacSocialPreviewWizard(models.TransientModel):
    """
    Preview wizard for vac.social.fb / vac.social.ing — embeds the live
    public campaign page in an iframe so the admin sees exactly what a
    visitor sees.

    For unpublished campaigns the iframe points to the backend-only
    preview route (/social/<platform>/invite/<slug>/preview, auth='user')
    so the full registration form is always visible regardless of
    publish state.
    """
    _name = 'vac.social.preview.wizard'
    _description = 'Social Campaign Preview Wizard'

    source_model = fields.Char(string='Source Model', readonly=True)
    source_id = fields.Integer(string='Source Record ID', readonly=True)
    title = fields.Char(string='Campaign Title', readonly=True)
    social_link = fields.Char(string='Campaign Link', readonly=True)
    published = fields.Boolean(string='Currently Published', readonly=True)
    preview_url = fields.Char(
        string='Preview URL',
        compute='_compute_preview_url',
    )
    preview_html = fields.Html(
        string='Live Preview',
        compute='_compute_preview_html',
        sanitize=False,
    )

    @api.depends('social_link')
    def _compute_preview_url(self):
        """
        Build the backend-only preview URL by appending '/preview' to
        the social_link.  Example:
          /social/fb/invite/my-campaign  →  /social/fb/invite/my-campaign/preview
        The route uses auth='user', so the logged-in backend user's
        session cookie grants access without extra tokens.
        """
        for wizard in self:
            if wizard.social_link:
                wizard.preview_url = wizard.social_link.rstrip('/') + '/preview'
            else:
                wizard.preview_url = False

    @api.depends('preview_url', 'title')
    def _compute_preview_html(self):
        for wizard in self:
            wizard.preview_html = _build_preview_html(
                wizard.preview_url, wizard.title)

    def action_publish_now(self):
        """Publish the social campaign from the preview wizard."""
        self.ensure_one()
        if not self.source_model or not self.source_id:
            return False
        record = self.env[self.source_model].browse(self.source_id)
        if not record.exists():
            return False
        stage = self.env['vac.event.stage'].search(
            [('name', 'ilike', 'Published')], limit=1)
        vals = {'published': True}
        if stage:
            vals['stage_id'] = stage.id
        record.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Campaign Published!',
                'message': f'"{self.title}" is now live.',
                'type': 'success',
                'sticky': False,
            },
        }
