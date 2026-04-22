# -*- coding: utf-8 -*-
"""
Helpdesk Student REST API — Ticket Controller
=============================================

Endpoints
---------
GET  /api/v1/helpdesk/tickets
    List all tickets for a student (identified by ``email`` query param).

GET  /api/v1/helpdesk/tickets/<ticket_id>
    Full detail for a single ticket belonging to that student.

Authentication
--------------
All routes require a valid JWT **access token**::

    Authorization: Bearer <access_token>

Obtain one from  ``POST /api/v1/auth/login``.

Error codes
-----------
400  MISSING_EMAIL      – email query param absent or blank
400  VALIDATION_ERROR   – bad pagination / sort value
401  MISSING_AUTH       – no Authorization header
401  TOKEN_EXPIRED      – access token has expired (use /refresh)
401  TOKEN_REVOKED      – token has been logged out
401  INVALID_TOKEN      – malformed / tampered token
404  STUDENT_NOT_FOUND  – no partner found for the given e-mail
404  TICKET_NOT_FOUND   – ticket not found or belongs to another student
500  INTERNAL_ERROR     – unexpected server error
"""

import logging

from odoo.exceptions import AccessError
from odoo.http import request, route, Controller

from ..utils.api_helpers import (
    error_response,
    require_jwt,
    resolve_partner_by_email,
    serialize_ticket_detail,
    serialize_ticket_list_item,
    success_response,
)

_logger = logging.getLogger(__name__)

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE     = 100
_VALID_SORT_FIELDS = {
    'create_date': 'create_date',
    'name':        'name',
    'stage':       'stage_id',
}
_VALID_SORT_DIRS = ('asc', 'desc')


class HelpdeskStudentAPIController(Controller):

    # -----------------------------------------------------------------------
    # 1. LIST  ─  GET /api/v1/helpdesk/tickets?email=student@example.com
    # -----------------------------------------------------------------------

    @route(
        '/api/v1/helpdesk/tickets',
        type='http',
        auth='none',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    @require_jwt
    def list_student_tickets(self, **params):
        """
        Return ALL helpdesk tickets belonging to the student identified by
        the ``email`` query parameter.

        The email is looked up against ``res.partner``.  Tickets are matched
        on ``partner_id`` **or** ``partner_email`` (covers agent-created tickets).

        Query Parameters
        ----------------
        email       str   REQUIRED – student e-mail address
        page        int   optional – 1-based page number         (default: 1)
        page_size   int   optional – records per page            (default: 20, max 100)
        status      str   optional – partial case-insensitive stage name match
        sort_by     str   optional – create_date | name | stage  (default: create_date)
        sort_dir    str   optional – asc | desc                  (default: desc)

        Success Response ``200``
        ------------------------
        {
            "status": "success",
            "data": [
                {
                    "id": 12,
                    "ticket_ref": "HEL00012",
                    "subject": "Cannot access portal",
                    "status": "New",
                    "create_date": "2025-03-10T08:22:00Z"
                }
            ],
            "meta": {
                "student_email": "john@university.com",
                "student_name":  "John Smith",
                "total_count":   5,
                "page":          1,
                "page_size":     20,
                "total_pages":   1
            }
        }
        """
        # Strip the injected JWT payload key so it doesn't pollute param parsing
        params.pop('_jwt_payload', None)

        try:
            # ── 1. Require email ─────────────────────────────────────────
            email = (params.get('email') or '').strip()
            if not email:
                return error_response(
                    400, 'MISSING_EMAIL',
                    'Query parameter "email" is required. '
                    'Example: /api/v1/helpdesk/tickets?email=student@university.com',
                )

            # ── 2. Resolve partner ───────────────────────────────────────
            partner = resolve_partner_by_email(email)
            if not partner:
                return error_response(
                    404, 'STUDENT_NOT_FOUND',
                    f'No student record found for email: {email}',
                )

            # ── 3. Parse optional params ─────────────────────────────────
            try:
                page      = max(1, int(params.get('page', 1)))
                page_size = min(
                    _MAX_PAGE_SIZE,
                    max(1, int(params.get('page_size', _DEFAULT_PAGE_SIZE))),
                )
            except (ValueError, TypeError):
                return error_response(
                    400, 'VALIDATION_ERROR',
                    '"page" and "page_size" must be positive integers.',
                )

            status_filter = (params.get('status')   or '').strip()
            sort_by       = (params.get('sort_by')   or 'create_date').strip()
            sort_dir      = (params.get('sort_dir')  or 'desc').strip().lower()

            if sort_by not in _VALID_SORT_FIELDS:
                return error_response(
                    400, 'VALIDATION_ERROR',
                    f'"sort_by" must be one of: {", ".join(_VALID_SORT_FIELDS)}.',
                )
            if sort_dir not in _VALID_SORT_DIRS:
                return error_response(
                    400, 'VALIDATION_ERROR',
                    '"sort_dir" must be "asc" or "desc".',
                )

            # ── 4. Build ORM domain ──────────────────────────────────────
            domain = [
                '|',
                ('partner_id',    '=',     partner.id),
                ('partner_email', '=ilike', email),
            ]

            if status_filter:
                stages = request.env['helpdesk.stage'].sudo().search(
                    [('name', 'ilike', status_filter)]
                )
                if not stages:
                    return success_response(
                        [],
                        meta={
                            'student_email': email,
                            'student_name':  partner.name,
                            'total_count':   0,
                            'page':          page,
                            'page_size':     page_size,
                            'total_pages':   0,
                        },
                    )
                domain.append(('stage_id', 'in', stages.ids))

            # ── 5. Query ─────────────────────────────────────────────────
            Ticket = request.env['helpdesk.ticket'].sudo()
            order  = f'{_VALID_SORT_FIELDS[sort_by]} {sort_dir}, id desc'

            total_count = Ticket.search_count(domain)
            total_pages = max(1, -(-total_count // page_size))
            offset      = (page - 1) * page_size

            tickets = Ticket.search(
                domain, order=order, limit=page_size, offset=offset
            )

            _logger.info(
                'list_student_tickets: email=%s → %d ticket(s)', email, total_count
            )

            return success_response(
                [serialize_ticket_list_item(t) for t in tickets],
                meta={
                    'student_email': email,
                    'student_name':  partner.name,
                    'total_count':   total_count,
                    'page':          page,
                    'page_size':     page_size,
                    'total_pages':   total_pages,
                },
            )

        except AccessError as exc:
            _logger.warning('Access error listing tickets email=%s: %s',
                            params.get('email'), exc)
            return error_response(403, 'FORBIDDEN', str(exc))
        except Exception as exc:
            _logger.exception('Unexpected error in list_student_tickets: %s', exc)
            return error_response(500, 'INTERNAL_ERROR',
                                  'An unexpected error occurred.')

    # -----------------------------------------------------------------------
    # 2. DETAIL  ─  GET /api/v1/helpdesk/tickets/<ticket_id>?email=...
    # -----------------------------------------------------------------------

    @route(
        '/api/v1/helpdesk/tickets/<int:ticket_id>',
        type='http',
        auth='none',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    @require_jwt
    def get_ticket_detail(self, ticket_id: int, **params):
        """
        Return full detail for a single helpdesk ticket.

        Ownership is validated: the ticket must belong to the student
        identified by ``email``.  If not, ``404`` is returned (not ``403``)
        to avoid leaking the existence of other students' tickets.

        Path Parameter
        --------------
        ticket_id   int   REQUIRED – internal Odoo ID

        Query Parameter
        ---------------
        email       str   REQUIRED – student e-mail (ownership check)

        Success Response ``200``
        ------------------------
        {
            "status": "success",
            "data": {
                "id":          12,
                "ticket_ref":  "HEL00012",
                "subject":     "Cannot access student portal",
                "status":      "In Progress",
                "create_date": "2025-03-10T08:22:00Z",
                "team":        "Student Support",
                "description": "<p>…</p>",
                "communication_history": [ … ],
                "attachments": [ … ]
            }
        }
        """
        params.pop('_jwt_payload', None)

        try:
            # ── 1. Require email ─────────────────────────────────────────
            email = (params.get('email') or '').strip()
            if not email:
                return error_response(
                    400, 'MISSING_EMAIL',
                    'Query parameter "email" is required. '
                    f'Example: /api/v1/helpdesk/tickets/{ticket_id}'
                    f'?email=student@university.com',
                )

            # ── 2. Resolve partner ───────────────────────────────────────
            partner = resolve_partner_by_email(email)
            if not partner:
                return error_response(
                    404, 'STUDENT_NOT_FOUND',
                    f'No student record found for email: {email}',
                )

            # ── 3. Fetch ticket ──────────────────────────────────────────
            ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
            if not ticket.exists():
                return error_response(
                    404, 'TICKET_NOT_FOUND',
                    f'Ticket {ticket_id} does not exist.',
                )

            # ── 4. Ownership check ───────────────────────────────────────
            owned_by_partner = (ticket.partner_id.id == partner.id)
            owned_by_email   = (
                (ticket.partner_email or '').strip().lower() == email.lower()
            )

            if not (owned_by_partner or owned_by_email):
                _logger.warning(
                    'get_ticket_detail: ticket %s does not belong to email=%s',
                    ticket_id, email,
                )
                return error_response(
                    404, 'TICKET_NOT_FOUND',
                    f'Ticket {ticket_id} does not exist.',
                )

            _logger.info('get_ticket_detail: email=%s ticket=%s OK', email, ticket_id)
            return success_response(serialize_ticket_detail(ticket))

        except AccessError as exc:
            _logger.warning('Access error ticket=%s email=%s: %s',
                            ticket_id, params.get('email'), exc)
            return error_response(
                404, 'TICKET_NOT_FOUND',
                f'Ticket {ticket_id} does not exist.',
            )
        except Exception as exc:
            _logger.exception(
                'Unexpected error in get_ticket_detail ticket_id=%s: %s',
                ticket_id, exc,
            )
            return error_response(500, 'INTERNAL_ERROR',
                                  'An unexpected error occurred.')
