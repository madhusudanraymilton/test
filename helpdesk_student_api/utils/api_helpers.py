# -*- coding: utf-8 -*-
"""
Shared helpers for the Helpdesk Student REST API.

Responsibilities
----------------
- ``require_jwt``   decorator  – validates Bearer JWT on every protected route
- Partner resolution from student e-mail
- Uniform JSON response builders  (success / error)
- Ticket serialisers              (list item vs. full detail)
"""

import json
import logging
from functools import wraps

from odoo.http import request, Response

from .jwt_utils import JWTError, decode_token

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def _json_response(data: dict, status: int = 200) -> Response:
    return Response(
        json.dumps(data, default=str),
        status=status,
        content_type='application/json; charset=utf-8',
    )


def success_response(data, *, meta: dict = None) -> Response:
    payload = {'status': 'success', 'data': data}
    if meta:
        payload['meta'] = meta
    return _json_response(payload, 200)


def error_response(http_status: int, code: str, message: str) -> Response:
    return _json_response(
        {'status': 'error', 'error': {'code': code, 'message': message}},
        http_status,
    )


# ---------------------------------------------------------------------------
# JWT authentication decorator
# ---------------------------------------------------------------------------

def require_jwt(fn):
    """
    Protect a route with JWT Bearer authentication.

    Expects::

        Authorization: Bearer <access_token>

    On success
    ----------
    - Decodes and validates the access token (signature, expiry, blacklist).
    - Calls ``request.update_env(user=uid)`` so the handler runs as the
      token owner.
    - Injects the decoded payload into ``kwargs['_jwt_payload']`` so
      handlers can read ``uid``, ``email``, ``partner_id`` etc. without
      re-decoding.

    On failure
    ----------
    Returns a 401 JSON response immediately; the wrapped function is never
    called.

    Usage::

        @route('/api/v1/...', type='http', auth='none', ...)
        @require_jwt
        def my_handler(self, **kwargs):
            payload = kwargs['_jwt_payload']
            uid     = payload['uid']
            ...
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.httprequest.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return error_response(
                401, 'MISSING_AUTH',
                'Authorization header required. '
                'Format: "Authorization: Bearer <access_token>"',
            )

        raw_token = auth_header[len('Bearer '):]

        try:
            payload = decode_token(raw_token, request.env, expected_type='access')
        except JWTError as exc:
            _logger.debug('JWT validation failed: %s – %s', exc.code, exc.message)
            return error_response(401, exc.code, exc.message)
        except Exception as exc:
            _logger.exception('Unexpected JWT error: %s', exc)
            return error_response(500, 'INTERNAL_ERROR',
                                  'An unexpected error occurred.')

        uid = payload.get('uid')
        if not uid:
            return error_response(401, 'INVALID_TOKEN',
                                  'Token payload is missing uid claim.')

        request.update_env(user=uid)
        kwargs['_jwt_payload'] = payload
        _logger.debug('JWT validated → uid=%s email=%s', uid, payload.get('email'))

        return fn(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Partner resolution  (by student e-mail)
# ---------------------------------------------------------------------------

def resolve_partner_by_email(email: str):
    """
    Return the first ``res.partner`` whose e-mail matches *email*
    (case-insensitive exact match), or ``None`` when not found.
    """
    if not email or not email.strip():
        return None

    partner = (
        request.env['res.partner']
        .sudo()
        .search([('email', '=ilike', email.strip())], limit=1)
    )
    return partner or None


# ---------------------------------------------------------------------------
# Datetime helper
# ---------------------------------------------------------------------------

def _fmt_dt(dt) -> str | None:
    """ISO-8601 UTC string, or None."""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else None


# ---------------------------------------------------------------------------
# Ticket serialisers
# ---------------------------------------------------------------------------

def serialize_ticket_list_item(ticket) -> dict:
    """Lightweight payload — list endpoint."""
    return {
        'id':          ticket.id,
        'ticket_ref':  ticket.ticket_ref or f'HD{ticket.id:05d}',
        'subject':     ticket.name,
        'status':      ticket.stage_id.name if ticket.stage_id else None,
        'create_date': _fmt_dt(ticket.create_date),
    }


def serialize_ticket_detail(ticket) -> dict:
    """Full payload — detail endpoint."""
    return {
        'id':                    ticket.id,
        'ticket_ref':            ticket.ticket_ref or f'HD{ticket.id:05d}',
        'subject':               ticket.name,
        'status':                ticket.stage_id.name if ticket.stage_id else None,
        'create_date':           _fmt_dt(ticket.create_date),
        'team':                  ticket.team_id.name  if ticket.team_id  else None,
        'description':           ticket.description or '',
        'communication_history': _get_messages(ticket),
        'attachments':           _get_attachments(ticket),
    }


# ---------------------------------------------------------------------------
# Internal serialisation helpers
# ---------------------------------------------------------------------------

def _get_messages(ticket) -> list[dict]:
    """
    Human-written chatter messages, oldest first.
    Excludes automated log-notes, stage-change notifications, empty bodies.
    """
    messages = ticket.message_ids.filtered(
        lambda m: (
            m.message_type in ('comment', 'email', 'email_outgoing')
            and bool((m.body or '').strip())
        )
    ).sorted('date')

    result = []
    for msg in messages:
        result.append({
            'id':           msg.id,
            'date':         _fmt_dt(msg.date),
            'author':       msg.author_id.name if msg.author_id else 'Unknown',
            'author_id':    msg.author_id.id   if msg.author_id else None,
            'message_type': msg.message_type,
            'body':         msg.body,
            'attachments': [
                {
                    'id':       att.id,
                    'name':     att.name,
                    'mimetype': att.mimetype,
                    'url':      f'/web/content/{att.id}?download=true',
                }
                for att in msg.attachment_ids
            ],
        })

    return result


def _get_attachments(ticket) -> list[dict]:
    """All ``ir.attachment`` records linked directly to this ticket."""
    attachments = (
        request.env['ir.attachment']
        .sudo()
        .search([
            ('res_model', '=', 'helpdesk.ticket'),
            ('res_id',    '=', ticket.id),
        ])
    )

    return [
        {
            'id':          att.id,
            'name':        att.name,
            'mimetype':    att.mimetype,
            'file_size':   att.file_size,
            'url':         f'/web/content/{att.id}?download=true',
            'create_date': _fmt_dt(att.create_date),
        }
        for att in attachments
    ]
