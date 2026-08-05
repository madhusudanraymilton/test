# -*- coding: utf-8 -*-
import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VacEmailTemplateAssetController(http.Controller):
    _ALLOWED_FIELDS = {
        'header_logo',
        'header_bg_image',
        'body_bg_image',
        'footer_logo',
    }

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

    @http.route(
        '/vac/email-template/<int:template_id>/<string:field_name>/<path:filename>',
        type='http',
        auth='public',
        website=False,
        sitemap=False,
    )
    def email_template_image(self, template_id, field_name, filename=None, **kwargs):
        if field_name not in self._ALLOWED_FIELDS:
            return request.not_found()

        template = request.env['vac.mail.template.config'].sudo().browse(template_id)
        if not template.exists() or not template[field_name]:
            return request.not_found()

        try:
            image_data = base64.b64decode(template[field_name])
        except Exception as exc:
            _logger.warning(
                "Could not decode email template image %s/%s: %s",
                template_id,
                field_name,
                exc,
            )
            return request.not_found()

        return request.make_response(image_data, [
            ('Content-Type', self._detect_content_type(filename)),
            ('Content-Length', len(image_data)),
            ('Cache-Control', 'public, max-age=604800'),
        ])
