"""
zencore_helpdesk_conversion_api — controllers/main.py

Endpoints
─────────
  POST /api/v1/helpdesk/ticket/<ticket_id>/inbound_message
      Receive a portal message, log it as an internal chatter note,
      notify the assigned agent.  (Section 2)

  GET  /api/v1/helpdesk/ticket/<ticket_id>/conversation
      Return the ticket message history in one of three modes:

        mode=tree   (default) — fully nested parent → children tree.
                                Best for collapsible / sidebar UIs.

        mode=flat             — strict date-ascending flat list.
                                Ignores threading; good for simple logs.

        mode=hybrid           — chronological DFS timeline.
                                Root messages ordered by date; each root's
                                replies follow immediately (depth-first) so
                                threads stay together without nesting.
                                Every message carries depth + thread_root_id
                                so the frontend can indent without recursion.

  GET  /api/v1/helpdesk/ticket/<ticket_id>/message/<message_id>/thread
      Return a single message and all its nested descendants only.

Auth : None (public) on all three routes.

Conversation design
───────────────────
  mail.message.parent_id == False  → root / independent message
  mail.message.parent_id != False  → threaded reply

  The three modes above all draw from the same flat DB query; only the
  serialisation step differs.  _serialise_message() is mode-agnostic.
"""

import base64
import binascii
import json
import logging
import mimetypes
from html.parser import HTMLParser

from markupsafe import Markup, escape
from werkzeug.utils import secure_filename

from odoo import http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Tiny HTML → plain-text stripper
# mail.message bodies are stored as HTML; callers often need a readable preview.
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Author-type resolver
#
#   partner.user_ids  — all res.users records linked to this partner
#   user.share        — True  → portal user
#                     — False → internal (back-office) user
#   No users at all   → public / external contact
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_author_type(partner):
    """
    Classify a partner as one of three mutually exclusive types:
        'internal_user'  — Odoo back-office employee
        'portal_user'    — authenticated portal customer
        'public'         — unauthenticated / external contact
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


# ─────────────────────────────────────────────────────────────────────────────
# Message serialiser
#
# Converts one mail.message record into a plain dict.
# Does NOT recurse — tree / hybrid assembly is done in dedicated functions.
#
# Fields returned:
#   message_id          — DB id
#   parent_id           — DB id of parent message (null if root/independent)
#   body_html           — raw HTML body stored by Odoo
#   body_text           — plain-text stripped version (preview / search)
#   message_type        — 'comment' | 'email' | 'notification' | 'user_notification'
#   subtype_name        — human-readable subtype label ('Note', 'Discussions', …)
#   is_internal_note    — True when subtype is mail.mt_note
#   direction           — 'inbound'  (from portal / external)
#                          'outbound' (from assigned agent)
#                          'internal' (other internal staff / system)
#   date                — ISO-8601 UTC timestamp
#   author              — nested author object (see below)
#   reply_count         — number of direct children (populated during tree build)
#   replies             — [] placeholder; filled by _build_tree() only
#
# Author object:
#   id                  — res.partner id
#   name                — display name
#   email               — email address
#   user_type           — 'internal_user' | 'portal_user' | 'public'
#   is_assigned_agent   — True if this author is the ticket's assigned user
# ─────────────────────────────────────────────────────────────────────────────

def _serialise_message(msg, ticket):
    partner     = msg.author_id
    author_type = _resolve_author_type(partner)

    assigned_pid = (
        ticket.user_id.partner_id.id
        if ticket.user_id and ticket.user_id.partner_id
        else False
    )

    # direction:
    #   inbound  = sent by a portal/public user (came from outside Odoo)
    #   outbound = sent by the assigned internal agent
    #   internal = posted by any other internal user or the system
    if author_type in ('portal_user', 'public'):
        direction = 'inbound'
    elif assigned_pid and partner and partner.id == assigned_pid:
        direction = 'outbound'
    else:
        direction = 'internal'

    subtype      = msg.subtype_id
    mt_note_ref  = request.env.ref('mail.mt_note', raise_if_not_found=False)
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
        'attachments':      [
            {
                'id':       attachment.id,
                'name':     attachment.name,
                'mimetype': attachment.mimetype,
                'url':      '/web/content/%s?download=true' % attachment.id,
            }
            for attachment in msg.attachment_ids
        ],
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


def _normalise_orphan_parent_ids(flat_messages):
    """Treat parents outside the returned conversation as root messages."""
    message_ids = {msg['message_id'] for msg in flat_messages}
    for msg in flat_messages:
        if msg['parent_id'] and msg['parent_id'] not in message_ids:
            msg['parent_id'] = None
    return flat_messages


# ─────────────────────────────────────────────────────────────────────────────
# TREE builder — O(n)
#
# Converts a flat list of serialised dicts into a nested tree.
#
# Algorithm:
#   1. Index every message by its message_id.
#   2. Walk the list once; for each message that has a parent_id:
#        - If the parent is in our set  → attach as a reply child.
#        - If the parent is NOT in set  → treat as root (orphan root).
#   3. Sort every level by date ascending (oldest-first, chat-window style).
#
# Output shape:
#   [
#     { "message_id": 10, "parent_id": null,
#       "replies": [
#         { "message_id": 11, "parent_id": 10,
#           "replies": [ {"message_id": 13, "parent_id": 11, "replies": []} ]
#         },
#         { "message_id": 12, "parent_id": 10, "replies": [] }
#       ]
#     }
#   ]
# ─────────────────────────────────────────────────────────────────────────────

def _build_tree(flat_messages):
    """Return fully nested conversation tree (mode=tree)."""
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


# ─────────────────────────────────────────────────────────────────────────────
# HYBRID builder — O(n)
#
# Returns a flat, depth-annotated timeline where threads stay together.
#
# Strategy:
#   1. Build a children map  { parent_id → [child, …] }  in one pass.
#   2. Identify root messages (no parent, or parent outside this message set).
#   3. Sort roots by date ascending.
#   4. DFS from each root: emit the root, recurse into its children in date
#      order, emit them, recurse further — this keeps all replies immediately
#      adjacent to their thread root in chronological DFS order.
#
# Each message in the output gets two extra fields:
#   depth           — nesting level (0 = root, 1 = direct reply, …)
#   thread_root_id  — message_id of the root of the thread this belongs to
#
# The 'replies' key is stripped — it is irrelevant in a flat timeline.
#
# Example output:
#   [
#     { "message_id": 10, "parent_id": null,  "depth": 0, "thread_root_id": 10 },
#     { "message_id": 11, "parent_id": 10,    "depth": 1, "thread_root_id": 10 },
#     { "message_id": 13, "parent_id": 11,    "depth": 2, "thread_root_id": 10 },
#     { "message_id": 12, "parent_id": 10,    "depth": 1, "thread_root_id": 10 },
#     { "message_id": 20, "parent_id": null,  "depth": 0, "thread_root_id": 20 },
#     { "message_id": 30, "parent_id": null,  "depth": 0, "thread_root_id": 30 },
#     { "message_id": 31, "parent_id": 30,    "depth": 1, "thread_root_id": 30 },
#   ]
# ─────────────────────────────────────────────────────────────────────────────

def _build_hybrid(flat_messages):
    """
    Return a chronological DFS timeline with depth and thread_root_id metadata
    (mode=hybrid).

    Roots are ordered by their own date.  Within each thread the DFS walk
    visits children in date-ascending order so the oldest reply appears before
    newer siblings.
    """
    mid_set       = {m['message_id'] for m in flat_messages}
    children_map  = {}   # { parent_id: [child_dict, …] }
    roots         = []

    for msg in flat_messages:
        pid = msg['parent_id']
        if pid and pid in mid_set:
            children_map.setdefault(pid, []).append(msg)
        else:
            roots.append(msg)

    # Sort roots and each children list by date, oldest first
    roots.sort(key=lambda m: m['date'] or '')
    for kids in children_map.values():
        kids.sort(key=lambda m: m['date'] or '')

    timeline = []

    def _dfs(msg, depth, thread_root_id):
        entry = {
            k: v for k, v in msg.items()
            if k not in ('replies',)          # strip tree-specific key
        }
        entry['depth']          = depth
        entry['thread_root_id'] = thread_root_id
        timeline.append(entry)
        for child in children_map.get(msg['message_id'], []):
            _dfs(child, depth + 1, thread_root_id)

    for root in roots:
        _dfs(root, 0, root['message_id'])

    return timeline


# ─────────────────────────────────────────────────────────────────────────────
# Controller
# ─────────────────────────────────────────────────────────────────────────────

class HelpdeskConversationController(http.Controller):

    MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

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
        Return the ticket's full message history in one of three modes.

        Query parameters (all optional):
          mode              tree | flat | hybrid  (default: tree)
          include_internal  1|0   Include mt_note internal notes  (default: 1)
          include_system    1|0   Include system notifications    (default: 0)

        ── mode=tree ──────────────────────────────────────────────────────────
        Fully nested conversation tree.  Messages with parent_id appear inside
        their parent's 'replies' list at unlimited depth.

        Response shape:
          {
            "mode": "tree",
            "conversation": [
              {
                "message_id": 10, "parent_id": null,
                "reply_count": 2,
                "replies": [
                  { "message_id": 11, "parent_id": 10,
                    "reply_count": 1,
                    "replies": [
                      { "message_id": 13, "parent_id": 11,
                        "reply_count": 0, "replies": [] }
                    ]
                  },
                  { "message_id": 12, "parent_id": 10,
                    "reply_count": 0, "replies": [] }
                ]
              },
              { "message_id": 20, "parent_id": null,
                "reply_count": 0, "replies": [] }
            ]
          }

        ── mode=flat ──────────────────────────────────────────────────────────
        Strict date-ascending flat list.  Threading fields (reply_count,
        replies) are present but always 0/[].  No grouping.

        Response shape:
          {
            "mode": "flat",
            "conversation": [
              { "message_id": 10, "parent_id": null,  … },
              { "message_id": 11, "parent_id": 10,    … },
              { "message_id": 13, "parent_id": 11,    … },
              { "message_id": 12, "parent_id": 10,    … },
              { "message_id": 20, "parent_id": null,  … }
            ]
          }

        ── mode=hybrid ────────────────────────────────────────────────────────
        Chronological DFS timeline.  Thread replies appear immediately after
        their root, but no nesting in the JSON — purely flat with metadata.
        'replies' key is omitted.

        Response shape:
          {
            "mode": "hybrid",
            "conversation": [
              { "message_id": 10, "parent_id": null,  "depth": 0, "thread_root_id": 10 },
              { "message_id": 11, "parent_id": 10,    "depth": 1, "thread_root_id": 10 },
              { "message_id": 13, "parent_id": 11,    "depth": 2, "thread_root_id": 10 },
              { "message_id": 12, "parent_id": 10,    "depth": 1, "thread_root_id": 10 },
              { "message_id": 20, "parent_id": null,  "depth": 0, "thread_root_id": 20 }
            ]
          }

        Full envelope (same for all modes):
          {
            "status":         "success",
            "ticket_id":      12,
            "ticket_name":    "Enrollment Issue",
            "ticket_status":  "In Progress",
            "assigned_agent": {"id": 5, "name": "Jane", "email": "jane@co.com"},
            "total_messages": 8,
            "mode":           "hybrid",
            "conversation":   [ … ]
          }

        Error responses:
          404 — ticket not found
          400 — invalid mode value
          500 — unexpected server error
        """
        # ── Query param parsing ──────────────────────────────────────────────
        mode             = query_params.get('mode', 'tree').strip().lower()
        include_internal = query_params.get('include_internal', '1') != '0'
        include_system   = query_params.get('include_system',   '0') == '1'

        if mode not in ('tree', 'flat', 'hybrid'):
            return self._json_response(
                {
                    "status":  "error",
                    "message": "Invalid mode '%s'. Accepted values: tree, flat, hybrid." % mode,
                },
                status=400,
            )

        # ── Ticket lookup ────────────────────────────────────────────────────
        ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
        if not ticket.exists():
            return self._json_response(
                {"status": "error", "message": "Ticket #%s not found." % ticket_id},
                status=404,
            )

        # ── ORM domain ───────────────────────────────────────────────────────
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

        # ── Fetch messages ───────────────────────────────────────────────────
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

        flat_list = _normalise_orphan_parent_ids(
            [_serialise_message(msg, ticket) for msg in messages]
        )

        # ── Build output in requested mode ───────────────────────────────────
        if mode == 'tree':
            conversation = _build_tree(flat_list)
        elif mode == 'hybrid':
            conversation = _build_hybrid(flat_list)
        else:
            # flat: flat_list is already date-sorted; return as-is
            conversation = flat_list

        # ── Assigned agent summary ───────────────────────────────────────────
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
            'mode':           mode,
            'conversation':   conversation,
        })

    # =========================================================================
    # GET /api/v1/helpdesk/ticket/<ticket_id>/message/<message_id>/thread
    #
    # Return a SINGLE message and all its descendants only.
    # Useful for lazy-loading one sub-thread without fetching the whole ticket.
    # =========================================================================

    # @http.route(
    #     '/api/v1/helpdesk/ticket/<int:ticket_id>/message/<int:message_id>/thread',
    #     type='http',
    #     auth='public',
    #     methods=['GET'],
    #     csrf=False,
    #     save_session=False,
    # )
    # def get_message_thread(self, ticket_id, message_id, **query_params):
    #     """
    #     Return a specific message and all its nested replies.

    #     Query parameters (optional):
    #       mode   tree | hybrid   (default: tree)
    #              'flat' is not useful here — use the full conversation endpoint.

    #     Success response (200) — mode=tree:
    #       {
    #         "status":     "success",
    #         "ticket_id":  12,
    #         "mode":       "tree",
    #         "root": {
    #           "message_id": 45, "parent_id": null,
    #           "replies": [
    #             { "message_id": 46,
    #               "replies": [ {"message_id": 50, "replies": []} ]
    #             }
    #           ]
    #         }
    #       }

    #     Success response (200) — mode=hybrid:
    #       {
    #         "status":     "success",
    #         "ticket_id":  12,
    #         "mode":       "hybrid",
    #         "thread": [
    #           { "message_id": 45, "depth": 0, "thread_root_id": 45 },
    #           { "message_id": 46, "depth": 1, "thread_root_id": 45 },
    #           { "message_id": 50, "depth": 2, "thread_root_id": 45 }
    #         ]
    #       }
    #     """
    #     mode = query_params.get('mode', 'tree').strip().lower()
    #     if mode not in ('tree', 'hybrid'):
    #         return self._json_response(
    #             {
    #                 "status":  "error",
    #                 "message": "Invalid mode '%s' for this endpoint. Use tree or hybrid." % mode,
    #             },
    #             status=400,
    #         )

    #     # ── Ticket + message validation ──────────────────────────────────────
    #     ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
    #     if not ticket.exists():
    #         return self._json_response(
    #             {"status": "error", "message": "Ticket #%s not found." % ticket_id},
    #             status=404,
    #         )

    #     root_msg = request.env['mail.message'].sudo().browse(message_id)
    #     if (
    #         not root_msg.exists()
    #         or root_msg.model != 'helpdesk.ticket'
    #         or root_msg.res_id != ticket_id
    #     ):
    #         return self._json_response(
    #             {
    #                 "status":  "error",
    #                 "message": "Message #%s not found on ticket #%s." % (message_id, ticket_id),
    #             },
    #             status=404,
    #         )

    #     # ── Collect all descendants — iterative BFS over child_ids ───────────
    #     # Avoids recursive SQL; works with any Odoo-supported PG version.
    #     collected = {}
    #     queue     = [root_msg]

    #     while queue:
    #         current_batch = queue
    #         queue = []
    #         for msg in current_batch:
    #             if msg.id not in collected:
    #                 collected[msg.id] = msg
    #                 for child in msg.child_ids:
    #                     queue.append(child)

    #     flat_list = _normalise_orphan_parent_ids(
    #         [_serialise_message(m, ticket) for m in collected.values()]
    #     )

    #     if mode == 'tree':
    #         thread_tree = _build_tree(flat_list)
    #         root_node   = next(
    #             (n for n in thread_tree if n['message_id'] == message_id),
    #             thread_tree[0] if thread_tree else None,
    #         )
    #         return self._json_response({
    #             'status':    'success',
    #             'ticket_id': ticket.id,
    #             'mode':      'tree',
    #             'root':      root_node,
    #         })

    #     # hybrid
    #     thread = _build_hybrid(flat_list)
    #     return self._json_response({
    #         'status':    'success',
    #         'ticket_id': ticket.id,
    #         'mode':      'hybrid',
    #         'thread':    thread,
    #     })

    # =========================================================================
    # POST /api/v1/helpdesk/ticket/<ticket_id>/inbound_message
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
            "parent_message_id": null,  // or integer — links to a specific reply
            "attachments": [
              {"filename": "screenshot.png", "data": "<base64>", "mimetype": "image/png"}
            ]
          }

        parent_message_id rules:
          null    → independent root message (no thread relationship)
          integer → threaded reply to that message_id

        Success (200):
          { "status": "success", "message_id": 45, "ticket_id": 12 }

        Errors: 400 | 404 | 422 | 500
        """
        # ── Parse request body ───────────────────────────────────────────────
        try:
            payload, uploaded_files = self._parse_inbound_payload()
        except ValueError as exc:
            return self._json_response(
                {"status": "error", "message": str(exc)},
                status=400,
            )

        sender_name     = str(payload.get('sender_name',  'Unknown Sender')).strip()
        sender_email    = str(payload.get('sender_email', '')).strip()
        body            = str(payload.get('body',         '')).strip()
        raw_parent      = payload.get('parent_message_id')
        raw_attachments = payload.get('attachments') or []

        if not body and not raw_attachments and not uploaded_files:
            return self._json_response(
                {"status": "error", "message": "'body' or 'attachments' is required."},
                status=422,
            )

        # ── Fetch ticket ─────────────────────────────────────────────────────
        ticket = request.env['helpdesk.ticket'].sudo().browse(ticket_id)
        if not ticket.exists():
            return self._json_response(
                {"status": "error", "message": "Ticket #%s not found." % ticket_id},
                status=404,
            )

        # ── Resolve author ───────────────────────────────────────────────────
        # Inbound portal messages must look like customer messages in chatter.
        # If the external sender is not in Odoo yet, create a lightweight contact
        # instead of posting as OdooBot, otherwise direction/reply styling breaks.
        author_id = False
        if sender_email:
            Partner = request.env['res.partner'].sudo()
            partner = Partner.search([('email', '=', sender_email)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': sender_name or sender_email,
                    'email': sender_email,
                })
            author_id = partner.id

        # ── Resolve optional parent_message_id ──────────────────────────────
        parent_id = self._resolve_parent_message_id(raw_parent, ticket_id)

        # ── Prepare optional inbound attachments ────────────────────────────
        try:
            attachments = self._prepare_inbound_attachments(raw_attachments)
            attachments += self._prepare_uploaded_attachments(uploaded_files)
        except ValueError as exc:
            return self._json_response(
                {"status": "error", "message": str(exc)},
                status=422,
            )
        except Exception as exc:
            _logger.error(
                "[Zencore] Failed to create attachments for ticket_id=%s: %s",
                ticket_id, exc,
            )
            return self._json_response(
                {"status": "error", "message": "Failed to process attachments."},
                status=500,
            )

        # ── Build chatter body ───────────────────────────────────────────────
        chatter_body = Markup("<p>%s</p>" % escape(body or ""))

        # ── Post to chatter ──────────────────────────────────────────────────
        # message_type='comment' + subtype_xmlid='mail.mt_note' → internal note.
        # _notify_thread is overridden on helpdesk.ticket (Section 1) so no
        # follower emails will be dispatched.
        # OdooBot is the default author when author_id=False, which intentionally
        # does NOT trigger the assigned-agent forward path in message_post().

        try:
            message = ticket.message_post(
                body=chatter_body,
                author_id=author_id or False,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
                parent_id=parent_id or False,
                attachments=attachments,
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

        # ── Notify assigned agent (Section 2) ────────────────────────────────
        ticket._notify_assigned_user_on_inbound()

        return self._json_response({
            "status":         "success",
            "message_id":     message.id,
            "ticket_id":      ticket.id,
            "attachment_ids": message.attachment_ids.ids,
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Shared private helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _parse_inbound_payload(self):
        """Support JSON base64 attachments and Postman multipart/form-data files."""
        content_type = (request.httprequest.content_type or '').lower()
        if content_type.startswith('multipart/form-data'):
            payload = dict(request.httprequest.form.items())
            attachments = payload.get('attachments')
            if attachments:
                try:
                    payload['attachments'] = json.loads(attachments)
                except (TypeError, ValueError):
                    raise ValueError("'attachments' must be valid JSON when sent as form-data.")

            uploaded_files = []
            for field_name in ('file', 'files', 'attachments_file'):
                uploaded_files.extend(request.httprequest.files.getlist(field_name))
            return payload, uploaded_files

        raw = request.httprequest.data
        if not raw:
            raise ValueError('Empty request body.')
        try:
            return json.loads(raw), []
        except (ValueError, TypeError) as exc:
            _logger.warning("[Zencore] Malformed JSON in inbound_message: %s", exc)
            raise ValueError('Invalid JSON payload.')

    @staticmethod
    def _prepare_inbound_attachments(raw_attachments):
        """Return message_post attachment tuples from JSON base64 payloads."""
        if not isinstance(raw_attachments, list):
            raise ValueError("'attachments' must be a list.")

        attachments = []
        for index, item in enumerate(raw_attachments, start=1):
            if not isinstance(item, dict):
                raise ValueError("Attachment #%s must be an object." % index)

            filename = HelpdeskConversationController._clean_filename(
                item.get('filename') or item.get('name') or 'attachment-%s' % index
            )
            raw_data = item.get('data') or item.get('datas') or item.get('content')
            if not raw_data:
                raise ValueError("Attachment '%s' is missing base64 data." % filename)

            raw_data = str(raw_data).strip()
            if ',' in raw_data and raw_data.lower().startswith('data:'):
                raw_data = raw_data.split(',', 1)[1]

            try:
                file_content = base64.b64decode(raw_data, validate=True)
            except (binascii.Error, ValueError):
                raise ValueError("Attachment '%s' has invalid base64 data." % filename)

            HelpdeskConversationController._check_attachment_size(filename, file_content)
            attachments.append((filename, file_content))
        return attachments

    @staticmethod
    def _prepare_uploaded_attachments(uploaded_files):
        """Return message_post attachment tuples from multipart FileStorage objects."""
        attachments = []
        for uploaded_file in uploaded_files:
            if not uploaded_file or not uploaded_file.filename:
                continue
            filename = HelpdeskConversationController._clean_filename(uploaded_file.filename)
            file_content = uploaded_file.read()
            HelpdeskConversationController._check_attachment_size(filename, file_content)
            attachments.append((filename, file_content))
        return attachments

    @staticmethod
    def _check_attachment_size(filename, file_content):
        if len(file_content) > HelpdeskConversationController.MAX_ATTACHMENT_BYTES:
            raise ValueError("Attachment '%s' exceeds 10MB limit." % filename)

    @staticmethod
    def _clean_filename(filename):
        filename = secure_filename(str(filename or '').strip())
        return filename or 'attachment'


    @staticmethod
    def _json_response(data, status=200):
        """Serialize data to a JSON HTTP response with an explicit status code."""
        return Response(
            json.dumps(data, default=str),
            content_type='application/json; charset=utf-8',
            status=status,
        )

    @staticmethod
    def _resolve_parent_message_id(raw_parent, ticket_id):
        """
        Validate and resolve an optional parent_message_id from the request.

        Returns a valid mail.message integer id or False.
        Logs a warning and returns False if the value is invalid or the
        referenced message does not exist.

        All callers must pass parent_message_id through this method so the
        value is consistently validated before being stored in the DB.
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

        if parent_msg.model != 'helpdesk.ticket' or parent_msg.res_id != ticket_id:
            _logger.warning(
                "[Zencore] parent_message_id=%s does not belong to ticket_id=%s. Ignoring.",
                parent_int, ticket_id,
            )
            return False

        return parent_msg.id