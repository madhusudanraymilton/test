# """
# zencore_helpdesk_conversion_api — controllers/main.py

# Section 2: Public REST endpoint for inbound portal messages.

# Endpoint : POST /api/helpdesk/ticket/<ticket_id>/inbound_message
# Auth     : None (public)
# Content  : application/json

# Request body:
#     {
#         "sender_name":       "John Doe",
#         "sender_email":      "john@example.com",
#         "body":              "Hello, I need help with my enrollment.",
#         "parent_message_id": null          // or integer
#     }

# Success response (200):
#     {
#         "status":     "success",
#         "message_id": 45,
#         "ticket_id":  12
#     }

# Error responses:
#     400 — missing / malformed body
#     404 — ticket not found
#     422 — validation failure (empty message body)
#     500 — unexpected server error
# """

# import json
# import logging

# from odoo import http
# from odoo.http import Response, request
# from markupsafe import Markup

# _logger = logging.getLogger(__name__)


# class HelpdeskInboundController(http.Controller):

#     # ── Route ─────────────────────────────────────────────────────────────────
#     # type='http'  → we parse JSON manually and return a raw Response.
#     # This gives us full control over status codes and response shape,
#     # which is required for a proper REST bridge (Odoo's type='json' wraps
#     # the response in a JSON-RPC envelope that external callers don't expect).
#     # ──────────────────────────────────────────────────────────────────────────

#     @http.route(
#         '/api/v1/helpdesk/ticket/<int:ticket_id>/inbound_message',
#         type='http',
#         auth='public',
#         methods=['POST'],
#         csrf=False,
#         save_session=False,   #aa 
#     )
#     def inbound_message(self, ticket_id, **_kwargs):
#         """
#         Receive an inbound message from the external portal.

#         Steps:
#             1. Parse and validate JSON body.
#             2. Look up the helpdesk.ticket record (sudo).
#             3. Resolve optional parent_message_id to a mail.message id.
#             4. Post the message to the chatter as an internal note (mt_note).
#                _notify_thread is suppressed (Section 1) — no follower emails.
#             5. Call ticket._notify_assigned_user_on_inbound() to send a
#                lightweight no-thread email to the assigned agent.
#             6. Return {status, message_id, ticket_id}.
#         """

#         # ── 1. Parse JSON ──────────────────────────────────────────────────────
#         raw = request.httprequest.data
#         if not raw:
#             return self._json_response(
#                 {"status": "error", "message": "Empty request body."},
#                 status=400,
#             )

#         try:
#             payload = json.loads(raw)
#         except (ValueError, TypeError) as exc:
#             _logger.warning(
#                 "[Zencore] Malformed JSON in inbound_message for ticket_id=%s: %s",
#                 ticket_id, exc,
#             )
#             return self._json_response(
#                 {"status": "error", "message": "Invalid JSON payload."},
#                 status=400,
#             )

#         sender_name  = str(payload.get('sender_name',  'Unknown Sender')).strip()
#         sender_email = str(payload.get('sender_email', '')).strip()
#         body         = str(payload.get('body',         '')).strip()
#         raw_parent   = payload.get('parent_message_id')

#         # ── 2. Validate required fields ────────────────────────────────────────
#         if not body:
#             return self._json_response(
#                 {"status": "error", "message": "'body' is required and cannot be empty."},
#                 status=422,
#             )

#         #find the partner here and add author id for the message post, if not found then it will be posted by OdooBot
#         partner = request.env['res.partner'].sudo().search([('email', '=', sender_email)], limit=1)
#         author_id = partner.id

#         # ── 3. Fetch ticket ────────────────────────────────────────────────────
#         ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
#         if not ticket.exists():
#             return self._json_response(
#                 {"status": "error", "message": "Ticket #%s not found." % ticket_id},
#                 status=404,
#             )

#         # ── 4. Resolve parent_message_id (Section 4) ──────────────────────────
#         parent_id = self._resolve_parent_message_id(raw_parent, ticket_id)

#         # ── 5. Build chatter body ──────────────────────────────────────────────
#         #
#         # Displayed as an internal note (mt_note) so it is visible only to
#         # internal users.  The chatter is used purely as an audit log.
#         #
#         if sender_email:
#             chatter_body = Markup(
#                 "<p>%s</p>"
#                 % (body)
#             )
#         else:
#             chatter_body = Markup(
#                 "<p>%s</p>"
#                 % (body)
#             )

#         # ── 6. Post to chatter ─────────────────────────────────────────────────
#         #
#         # message_type='comment' + subtype_xmlid='mail.mt_note' → internal note.
#         # _notify_thread is overridden on helpdesk.ticket (Section 1) so no
#         # follower emails will be dispatched by this message_post call.
#         # The author defaults to the current sudo user (OdooBot), NOT the
#         # assigned user — so the Section 3 forward will NOT be triggered here.
#         #
#         try:
#             message = ticket.message_post(
#                 body=chatter_body,
#                 author_id=author_id,
#                 message_type='comment',
#                 subtype_xmlid='mail.mt_note',
#                 parent_id=parent_id or False,
#             )
#         except Exception as exc:
#             _logger.error(
#                 "[Zencore] Failed to post chatter message for ticket_id=%s: %s",
#                 ticket_id, exc,
#             )
#             return self._json_response(
#                 {"status": "error", "message": "Failed to post message."},
#                 status=500,
#             )

#         # ── 7. Notify assigned user (Section 2 spec) ───────────────────────────
#         ticket._notify_assigned_user_on_inbound()

#         # ── 8. Return success ──────────────────────────────────────────────────
#         return self._json_response({
#             "status":     "success",
#             "message_id": message.id,
#             "ticket_id":  ticket.id,
#         })

#     # ── Private helpers ───────────────────────────────────────────────────────

#     @staticmethod
#     def _json_response(data, status=200):
#         """
#         Return a raw HTTP Response with JSON content type and an explicit
#         HTTP status code.

#         Always use this helper — never return a plain dict from http routes,
#         as that would render as a string, not valid JSON.
#         """
#         return Response(
#             json.dumps(data),
#             content_type='application/json; charset=utf-8',
#             status=status,
#         )

#     @staticmethod
#     def _resolve_parent_message_id(raw_parent, ticket_id):
#         """
#         Validate and resolve the optional parent_message_id from the request.

#         Returns a valid mail.message id (int) or False.
#         Logs a warning and returns False if the value is invalid or the
#         referenced message does not exist.

#         Section 4: all callers must pass parent_message_id through this method
#         so the value is consistently validated before being stored in the DB.
#         """
#         if raw_parent is None:
#             return False

#         try:
#             parent_int = int(raw_parent)
#         except (ValueError, TypeError):
#             _logger.warning(
#                 "[Zencore] parent_message_id='%s' is not an integer "
#                 "(ticket_id=%s). Ignoring.",
#                 raw_parent, ticket_id,
#             )
#             return False

#         parent_msg = request.env['mail.message'].sudo().browse(parent_int)
#         if not parent_msg.exists():
#             _logger.warning(
#                 "[Zencore] parent_message_id=%s does not exist "
#                 "(ticket_id=%s). Ignoring.",
#                 parent_int, ticket_id,
#             )
#             return False

#         return parent_msg.id
    
"""
zencore_helpdesk_conversion_api — controllers/main.py

Endpoints:

  POST /api/v1/helpdesk/ticket/<ticket_id>/inbound_message
      Receive a portal message, log it as an internal chatter note,
      and notify the assigned agent.  (Section 2)

  GET  /api/v1/helpdesk/ticket/<ticket_id>/conversation
      Return the full threaded message history for a ticket.
      Supports parent -> child -> grandchild nesting at unlimited depth.
      Identifies each author as internal_user | portal_user | public.

  GET  /api/v1/helpdesk/ticket/<ticket_id>/message/<message_id>/thread
      Return a single message and all its nested descendants only.
      Useful for lazy-loading a sub-thread without fetching the full ticket.

Auth : None (public) on all routes.
"""

import json
import logging
from html.parser import HTMLParser
from markupsafe import Markup

from odoo import http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tiny HTML -> plain-text stripper
# mail.message stores body as HTML; callers often need a readable preview.
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return ' '.join(self._parts).strip()


def _strip_html(html):
    if not html:
        return ''
    stripper = _HTMLStripper()
    try:
        stripper.feed(html)
        return stripper.get_text()
    except Exception:
        return html


# ---------------------------------------------------------------------------
# Author-type resolver
#
# partner.user_ids  -- all res.users records linked to this partner
# user.share        -- True  -> portal user
#                   -- False -> internal (back-office) user
# No users at all   -> public / external contact
# ---------------------------------------------------------------------------

def _resolve_author_type(partner):
    """
    Classify the partner as one of three mutually exclusive types:
        'internal_user'  -- Odoo back-office employee
        'portal_user'    -- authenticated portal customer
        'public'         -- unauthenticated / external contact
    """
    if not partner:
        return 'public'
    users = partner.user_ids
    if not users:
        return 'public'
    for user in users:
        if not user.share:
            return 'internal_user'
    return 'portal_user'


# ---------------------------------------------------------------------------
# Message serialiser
#
# Converts a single mail.message record into a plain dict.
# Does NOT recurse -- tree assembly is done separately in _build_tree().
# ---------------------------------------------------------------------------

def _serialise_message(msg, ticket):
    """
    Return a flat dict representing one mail.message record.

    Fields returned per message:
        message_id          -- DB id of this message
        parent_id           -- DB id of parent message (null if root)
        body_html           -- raw HTML body stored by Odoo
        body_text           -- plain-text stripped version (preview / search)
        message_type        -- 'comment' | 'email' | 'notification' | 'user_notification'
        subtype_name        -- human-readable subtype label (e.g. 'Note', 'Discussions')
        is_internal_note    -- True when subtype is mail.mt_note
        direction           -- 'inbound'  (from portal / external)
                               'outbound' (from assigned agent)
                               'internal' (other internal staff / system)
        date                -- ISO-8601 UTC timestamp
        author              -- nested author object (see below)
        reply_count         -- number of direct children (filled during tree build)
        replies             -- [] placeholder, filled by _build_tree()

    Author object fields:
        id                  -- res.partner id
        name                -- display name
        email               -- email address
        user_type           -- 'internal_user' | 'portal_user' | 'public'
        is_assigned_agent   -- True if this author is the ticket's assigned user
    """
    partner     = msg.author_id
    author_type = _resolve_author_type(partner)

    assigned_pid = (
        ticket.user_id.partner_id.id
        if ticket.user_id and ticket.user_id.partner_id
        else False
    )

    # Direction logic:
    #   inbound  = sent by a portal/public user (came from outside Odoo)
    #   outbound = sent by the assigned internal agent
    #   internal = posted by any other internal user or the system
    if author_type in ('portal_user', 'public'):
        direction = 'inbound'
    elif assigned_pid and partner and partner.id == assigned_pid:
        direction = 'outbound'
    else:
        direction = 'internal'

    subtype = msg.subtype_id
    mt_note_ref = request.env.ref('mail.mt_note', raise_if_not_found=False)
    is_internal_note = bool(
        subtype and mt_note_ref and subtype.id == mt_note_ref.id
    )

    return {
        'message_id':       msg.id,
        'parent_id':        msg.parent_id.id if msg.parent_id else None,
        'body_html':        msg.body or '',
        'body_text':        _strip_html(msg.body),
        'message_type':     msg.message_type or '',
        'subtype_name':     subtype.name if subtype else None,
        'is_internal_note': is_internal_note,
        'direction':        direction,
        'date':             msg.date.strftime('%Y-%m-%dT%H:%M:%SZ') if msg.date else None,
        'author': {
            'id':                partner.id if partner else None,
            'name':              partner.name if partner else 'Unknown',
            'email':             partner.email if partner else None,
            'user_type':         author_type,
            'is_assigned_agent': bool(
                assigned_pid and partner and partner.id == assigned_pid
            ),
        },
        'reply_count': 0,
        'replies':     [],
    }


# ---------------------------------------------------------------------------
# Tree builder  O(n)
#
# Converts a flat list of serialised message dicts into a nested tree.
#
# Algorithm:
#   1. Index every message by its message_id.
#   2. Walk the list once; for each message that has a parent_id:
#        - If the parent is in our set -> attach as a reply child.
#        - If the parent is NOT in our set -> treat as root.
#   3. Root messages: parent_id=null OR parent absent from the current set.
#   4. Sort every level by date ascending (oldest first, like a chat window).
# ---------------------------------------------------------------------------

def _build_tree(flat_messages):
    """
    Build a nested conversation tree from a flat list of serialised messages.

    Returns a list of root-level message dicts, each with a populated
    'replies' list that may itself contain further nested 'replies'.

    Output shape example:
        [
          {
            "message_id": 10,
            "parent_id": null,
            "replies": [
              {
                "message_id": 11,
                "parent_id": 10,
                "replies": [
                  {"message_id": 13, "parent_id": 11, "replies": []}
                ]
              },
              {"message_id": 12, "parent_id": 10, "replies": []}
            ]
          }
        ]
    """
    index = {m['message_id']: m for m in flat_messages}
    roots = []

    for msg in flat_messages:
        pid = msg['parent_id']
        if pid and pid in index:
            parent = index[pid]
            parent['replies'].append(msg)
            parent['reply_count'] += 1
        else:
            roots.append(msg)

    def _sort_level(nodes):
        nodes.sort(key=lambda m: m['date'] or '')
        for node in nodes:
            if node['replies']:
                _sort_level(node['replies'])

    _sort_level(roots)
    return roots


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class HelpdeskConversationController(http.Controller):

    # =========================================================================
    # GET /api/v1/helpdesk/ticket/<ticket_id>/conversation
    # =========================================================================

    @http.route(
        '/api/v1/helpdesk/ticket/<int:ticket_id>/conversation',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def get_conversation(self, ticket_id, **query_params):
        """
        Return the full threaded conversation for a helpdesk ticket.

        Query parameters (all optional):
            include_internal  1|0  Include mt_note internal notes (default: 1)
            include_system    1|0  Include system notifications   (default: 0)
            flat              1|0  Return flat list, not a tree   (default: 0)

        Success response (200):
        {
          "status":         "success",
          "ticket_id":      12,
          "ticket_name":    "Enrollment Issue",
          "ticket_status":  "In Progress",
          "assigned_agent": {"id": 5, "name": "Jane Agent", "email": "jane@co.com"},
          "total_messages": 8,
          "conversation": [
            {
              "message_id": 45,
              "parent_id":  null,
              "body_html":  "<p>Hello I need help...</p>",
              "body_text":  "Hello I need help...",
              "message_type": "comment",
              "subtype_name": "Note",
              "is_internal_note": true,
              "direction":  "inbound",
              "date":       "2025-01-15T10:30:00Z",
              "author": {
                  "id": 22,
                  "name": "John Doe",
                  "email": "john@example.com",
                  "user_type": "portal_user",
                  "is_assigned_agent": false
              },
              "reply_count": 2,
              "replies": [
                {
                  "message_id": 46,
                  "parent_id":  45,
                  "direction":  "outbound",
                  "reply_count": 1,
                  "replies": [
                    {
                      "message_id": 50,
                      "parent_id":  46,
                      "direction":  "inbound",
                      "replies": []
                    }
                  ]
                }
              ]
            }
          ]
        }
        """
        include_internal = query_params.get('include_internal', '1') != '0'
        include_system   = query_params.get('include_system',   '0') == '1'
        return_flat      = query_params.get('flat',             '0') == '1'

        ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
        if not ticket.exists():
            return self._json_response(
                {"status": "error", "message": "Ticket #%s not found." % ticket_id},
                status=404,
            )

        # Build ORM domain
        allowed_types = ['comment', 'email']
        if include_system:
            allowed_types += ['notification', 'user_notification']

        domain = [
            ('model',        '=',  'helpdesk.ticket'),
            ('res_id',       '=',  ticket_id),
            ('message_type', 'in', allowed_types),
        ]

        if not include_internal:
            mt_note = request.env.ref('mail.mt_note', raise_if_not_found=False)
            if mt_note:
                domain.append(('subtype_id', '!=', mt_note.id))

        try:
            messages = request.env['mail.message'].sudo().search(
                domain,
                order='date asc',
            )
        except Exception as exc:
            _logger.error(
                "[Zencore] Failed to fetch messages for ticket_id=%s: %s",
                ticket_id, exc,
            )
            return self._json_response(
                {"status": "error", "message": "Failed to retrieve conversation."},
                status=500,
            )

        flat_list    = [_serialise_message(msg, ticket) for msg in messages]
        conversation = flat_list if return_flat else _build_tree(flat_list)

        assigned_agent = None
        if ticket.user_id:
            assigned_agent = {
                'id':    ticket.user_id.id,
                'name':  ticket.user_id.name,
                'email': ticket.user_id.email,
            }

        return self._json_response({
            'status':         'success',
            'ticket_id':      ticket.id,
            'ticket_name':    ticket.name or '',
            'ticket_status':  ticket.stage_id.name if ticket.stage_id else None,
            'assigned_agent': assigned_agent,
            'total_messages': len(flat_list),
            'conversation':   conversation,
        })

    # =========================================================================
    # GET /api/helpdesk/ticket/<ticket_id>/message/<message_id>/thread
    #
    # Return a SINGLE message and all its descendants only.
    # Useful for lazy-loading one sub-thread without fetching the whole ticket.
    # =========================================================================

    @http.route(
        '/api/helpdesk/ticket/<int:ticket_id>/message/<int:message_id>/thread',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def get_message_thread(self, ticket_id, message_id, **_kwargs):
        """
        Return a specific message and all its nested replies.

        Success response (200):
        {
          "status":     "success",
          "ticket_id":  12,
          "root": {
            "message_id": 45,
            "parent_id":  null,
            "replies": [
              {
                "message_id": 46,
                "replies": [
                  {"message_id": 50, "replies": []}
                ]
              }
            ]
          }
        }
        """
        ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
        if not ticket.exists():
            return self._json_response(
                {"status": "error", "message": "Ticket #%s not found." % ticket_id},
                status=404,
            )

        root_msg = request.env['mail.message'].sudo().browse(message_id)
        if (
            not root_msg.exists()
            or root_msg.model != 'helpdesk.ticket'
            or root_msg.res_id != ticket_id
        ):
            return self._json_response(
                {
                    "status":  "error",
                    "message": "Message #%s not found on ticket #%s." % (message_id, ticket_id),
                },
                status=404,
            )

        # Collect all descendants using iterative BFS over child_ids.
        # This avoids recursive SQL and works with any Odoo-supported PG version.
        collected = {}
        queue     = [root_msg]

        while queue:
            current_batch = queue
            queue = []
            for msg in current_batch:
                if msg.id not in collected:
                    collected[msg.id] = msg
                    for child in msg.child_ids:
                        queue.append(child)

        flat_list   = [_serialise_message(m, ticket) for m in collected.values()]
        thread_tree = _build_tree(flat_list)

        root_node = next(
            (n for n in thread_tree if n['message_id'] == message_id),
            thread_tree[0] if thread_tree else None,
        )

        return self._json_response({
            'status':    'success',
            'ticket_id': ticket.id,
            'root':      root_node,
        })

    # =========================================================================
    # POST /api/v1/helpdesk/ticket/<ticket_id>/inbound_message   (Section 2)
    # =========================================================================

    @http.route(
        '/api/v1/helpdesk/ticket/<int:ticket_id>/inbound_message',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def inbound_message(self, ticket_id, **_kwargs):
        """
        Receive an inbound message from the external portal.

        Request body (JSON):
        {
            "sender_name":       "John Doe",
            "sender_email":      "john@example.com",
            "body":              "Hello, I need help with my enrollment.",
            "parent_message_id": null
        }

        Success (200): {"status": "success", "message_id": 45, "ticket_id": 12}
        Errors: 400 | 404 | 422 | 500
        """
        raw = request.httprequest.data
        if not raw:
            return self._json_response(
                {"status": "error", "message": "Empty request body."},
                status=400,
            )

        try:
            payload = json.loads(raw)
        except (ValueError, TypeError) as exc:
            _logger.warning(
                "[Zencore] Malformed JSON in inbound_message for ticket_id=%s: %s",
                ticket_id, exc,
            )
            return self._json_response(
                {"status": "error", "message": "Invalid JSON payload."},
                status=400,
            )

        sender_name  = str(payload.get('sender_name',  'Unknown Sender')).strip()
        sender_email = str(payload.get('sender_email', '')).strip()
        body         = str(payload.get('body',         '')).strip()
        raw_parent   = payload.get('parent_message_id')


        #find the partner here and add author id for the message post, if not found then it will be posted by OdooBot
        partner = request.env['res.partner'].sudo().search([('email', '=', sender_email)], limit=1)
        author_id = partner.id


        if not body:
            return self._json_response(
                {"status": "error", "message": "'body' is required and cannot be empty."},
                status=422,
            )

        ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
        if not ticket.exists():
            return self._json_response(
                {"status": "error", "message": "Ticket #%s not found." % ticket_id},
                status=404,
            )

        parent_id = self._resolve_parent_message_id(raw_parent, ticket_id)

        if sender_email:
            chatter_body = Markup(
                "<p>%s</p>"
                % (body)
            )
        else:
            chatter_body = Markup(
                "<p>%s</p>"
                % (body)
            )

        try:
            message = ticket.message_post(
                body=chatter_body,
                author_id=author_id,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
                parent_id=parent_id or False,
            )
        except Exception as exc:
            _logger.error(
                "[Zencore] Failed to post chatter message for ticket_id=%s: %s",
                ticket_id, exc,
            )
            return self._json_response(
                {"status": "error", "message": "Failed to post message."},
                status=500,
            )

        ticket._notify_assigned_user_on_inbound()

        return self._json_response({
            "status":     "success",
            "message_id": message.id,
            "ticket_id":  ticket.id,
        })

    # -------------------------------------------------------------------------
    # Shared private helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _json_response(data, status=200):
        """Serialize data to a JSON HTTP response with the given status code."""
        return Response(
            json.dumps(data, default=str),
            content_type='application/json; charset=utf-8',
            status=status,
        )

    @staticmethod
    def _resolve_parent_message_id(raw_parent, ticket_id):
        """
        Validate and resolve an optional parent_message_id.
        Returns a valid mail.message integer id or False.
        """
        if raw_parent is None:
            return False
        try:
            parent_int = int(raw_parent)
        except (ValueError, TypeError):
            _logger.warning(
                "[Zencore] parent_message_id='%s' is not an integer "
                "(ticket_id=%s). Ignoring.",
                raw_parent, ticket_id,
            )
            return False
        parent_msg = request.env['mail.message'].sudo().browse(parent_int)
        if not parent_msg.exists():
            _logger.warning(
                "[Zencore] parent_message_id=%s does not exist "
                "(ticket_id=%s). Ignoring.",
                parent_int, ticket_id,
            )
            return False
        return parent_msg.id