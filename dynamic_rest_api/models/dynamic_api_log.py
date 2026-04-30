# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class DynamicApiLog(models.Model):
    """
    Immutable request/response log for every call handled by the dynamic
    controller.  Provides audit trail, stats, and rate-limit data.

    Auto-cleanup: a scheduled action deletes records older than the retention
    period (default 30 days) configured in ir.config.parameter.
    """
    _name = 'dynamic.api.log'
    _description = 'Dynamic API Request Log'
    _order = 'timestamp desc'
    # Logs are append-only — prevent accidental writes via ORM override
    _log_access = False  # skip create_date/write_date (we store timestamp manually)

    endpoint_id = fields.Many2one(
        'dynamic.api.endpoint', string='Endpoint',
        ondelete='set null', index=True,
    )
    endpoint_path = fields.Char(
        string='Endpoint Path', readonly=True,
        help='Stored denormalised so logs survive endpoint deletion.',
    )
    method = fields.Char(string='HTTP Method', readonly=True)
    request_ip = fields.Char(string='Client IP', readonly=True)
    request_payload = fields.Text(
        string='Request Body (JSON)', readonly=True,
        help='Truncated at 4 KB for storage efficiency.',
    )
    response_code = fields.Integer(string='HTTP Status Code', readonly=True)
    response_time_ms = fields.Integer(string='Response Time (ms)', readonly=True)
    user_id = fields.Many2one(
        'res.users', string='Auth User', ondelete='set null',
    )
    api_key_id = fields.Many2one(
        'dynamic.api.key', string='API Key Used', ondelete='set null',
    )
    timestamp = fields.Datetime(
        string='Timestamp', readonly=True, index=True,
        default=fields.Datetime.now,
    )
    error_message = fields.Text(string='Error Message', readonly=True)
    # Stores the serialised query parameters for GET requests
    query_params = fields.Text(string='Query Parameters', readonly=True)

    # ─────────────────────────────────────────────────────────────────────────
    # ORM overrides
    # ─────────────────────────────────────────────────────────────────────────

    def write(self, vals):
        # Logs are immutable — silently ignore write attempts
        _logger.warning('DynamicApiLog: attempted write on log id=%s (ignored)', self.ids)
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Cleanup cron
    # ─────────────────────────────────────────────────────────────────────────

    @api.model
    def _cron_cleanup_old_logs(self):
        """
        Delete log entries older than the configured retention period.
        Configured via ir.config.parameter key:
          dynamic_rest_api.log_retention_days  (default: 30)
        """
        param = self.env['ir.config_parameter'].sudo().get_param(
            'dynamic_rest_api.log_retention_days', default='30',
        )
        try:
            days = int(param)
        except (ValueError, TypeError):
            days = 30

        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        old_logs = self.search([('timestamp', '<', cutoff)])
        count = len(old_logs)
        old_logs.unlink()
        _logger.info('DynamicApiLog: cleaned up %d records older than %d days.', count, days)
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Factory — used by controller to avoid boilerplate
    # ─────────────────────────────────────────────────────────────────────────

    @api.model
    def log_request(self, endpoint, method, request_ip,
                    payload_str, response_code, response_time_ms,
                    user=None, api_key=None, error=None, query_params=None):
        """
        Create a log entry.  Truncates payload to 4 096 bytes.
        Always uses sudo() since the controller may run as public.
        """
        MAX_PAYLOAD = 4096
        if payload_str and len(payload_str) > MAX_PAYLOAD:
            payload_str = payload_str[:MAX_PAYLOAD] + '... [truncated]'

        vals = {
            'endpoint_id': endpoint.id if endpoint else False,
            'endpoint_path': endpoint.endpoint_path if endpoint else 'unknown',
            'method': method,
            'request_ip': request_ip,
            'request_payload': payload_str,
            'response_code': response_code,
            'response_time_ms': response_time_ms,
            'timestamp': fields.Datetime.now(),
        }
        if user:
            vals['user_id'] = user.id
        if api_key:
            vals['api_key_id'] = api_key.id
        if error:
            vals['error_message'] = str(error)[:2048]
        if query_params:
            vals['query_params'] = str(query_params)[:1024]

        try:
            return self.sudo().create(vals)
        except Exception as e:
            _logger.error('DynamicApiLog: failed to write log: %s', e)
            return self.browse()
