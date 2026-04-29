# -*- coding: utf-8 -*-
"""
Dynamic REST API Dispatcher
============================

Architecture — "Registry Lookup at Request Time"
-------------------------------------------------
A single @http.route is registered at server boot:

    /api/dynamic/<path:endpoint_path>

This route never changes.  At each incoming HTTP request the handler:

  1. Reconstructs the full path  →  /api/dynamic/<slug>
  2. Looks up dynamic.api.endpoint in the DB (via ormcache — very fast)
  3. Validates auth (public / api_key / session)
  4. Dispatches to _handle_get / _handle_post / _handle_put / _handle_delete
  5. Serialises the ORM result using the endpoint's field alias map
  6. Writes a log entry
  7. Returns a standard JSON envelope

No Odoo restart is required when adding new endpoints.  The ormcache is busted
by dynamic.api.endpoint.write / create / unlink.  The next request after a
cache miss re-reads from the DB and re-populates the cache automatically.

Standard response envelope
--------------------------
{
    "success": true|false,
    "data":    <records | null>,
    "error":   <error_message | null>,
    "meta":    { "total": N, "page": P, "page_size": S, "method": "GET" }
}
"""
import json
import time
import logging
from odoo import http, api, SUPERUSER_ID, _
from odoo.http import request

_logger = logging.getLogger(__name__)

# Default pagination
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000


class DynamicApiController(http.Controller):
    """Single master controller for all dynamic REST endpoints."""

    # ─────────────────────────────────────────────────────────────────────────
    # Master route
    # ─────────────────────────────────────────────────────────────────────────

    @http.route(
        '/api/dynamic/<path:endpoint_path>',
        auth='none',
        type='http',
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        csrf=False,
        save_session=False,
        cors='*',
    )
    def dispatch(self, endpoint_path, **kwargs):
        """
        Entry point for every dynamic API call.

        The ``auth='none'`` means Odoo does not enforce session validation
        before calling this handler — we perform our own auth inside.
        ``type='http'`` gives us raw access to the HTTP request/response objects
        so we can parse the body ourselves and return JSON with custom headers.
        """
        start_time = time.monotonic()

        # Handle CORS pre-flight
        http_method = request.httprequest.method.upper()
        if http_method == 'OPTIONS':
            return self._cors_preflight_response()

        # Reconstruct full path as stored in the model
        full_path = f'/api/dynamic/{endpoint_path}'

        # ── Step 1: look up endpoint (cached) ────────────────────────────────
        env = request.env(user=SUPERUSER_ID)
        endpoint = env['dynamic.api.endpoint']._get_endpoint_for_request(full_path)

        if not endpoint:
            return self._json_response(
                {'success': False, 'data': None, 'error': 'Endpoint not found', 'meta': {}},
                status=404,
            )

        # ── Step 2: method allowed? ───────────────────────────────────────────
        allowed_methods = endpoint.get_allowed_methods()
        if http_method not in allowed_methods:
            return self._json_response(
                {
                    'success': False, 'data': None,
                    'error': f'Method {http_method} not allowed. Allowed: {allowed_methods}',
                    'meta': {},
                },
                status=405,
                extra_headers={'Allow': ', '.join(allowed_methods)},
            )

        # ── Step 3: authentication ────────────────────────────────────────────
        auth_user = None
        api_key_rec = None
        try:
            auth_user, api_key_rec = self._authenticate(endpoint, env)
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            env['dynamic.api.log'].log_request(
                endpoint, http_method,
                self._get_client_ip(), None, 401, elapsed_ms,
                error=str(exc),
            )
            return self._json_response(
                {'success': False, 'data': None, 'error': str(exc), 'meta': {}},
                status=401,
            )

        # ── Step 4: rate limiting ─────────────────────────────────────────────
        if api_key_rec and endpoint.rate_limit:
            if not api_key_rec.check_rate_limit(endpoint):
                return self._json_response(
                    {
                        'success': False, 'data': None,
                        'error': 'Rate limit exceeded. Please retry after a minute.',
                        'meta': {},
                    },
                    status=429,
                )

        # ── Step 5: parse request body ────────────────────────────────────────
        payload = {}
        raw_body = None
        if http_method in ('POST', 'PUT'):
            raw_body = request.httprequest.get_data(as_text=True)
            if raw_body:
                try:
                    payload = json.loads(raw_body)
                except json.JSONDecodeError as e:
                    return self._json_response(
                        {
                            'success': False, 'data': None,
                            'error': f'Invalid JSON body: {e}',
                            'meta': {},
                        },
                        status=400,
                    )

        # ── Step 6: dispatch ──────────────────────────────────────────────────
        try:
            if http_method == 'GET':
                response_body, status = self._handle_get(endpoint, env, kwargs)
            elif http_method == 'POST':
                response_body, status = self._handle_post(endpoint, env, payload)
            elif http_method == 'PUT':
                response_body, status = self._handle_put(endpoint, env, payload, kwargs)
            elif http_method == 'DELETE':
                response_body, status = self._handle_delete(endpoint, env, kwargs)
            else:
                response_body = {
                    'success': False, 'data': None,
                    'error': 'Unsupported method', 'meta': {},
                }
                status = 405
        except Exception as exc:
            _logger.exception('DynamicAPI: unhandled error in %s %s', http_method, full_path)
            response_body = {
                'success': False, 'data': None,
                'error': str(exc), 'meta': {},
            }
            status = 500

        # ── Step 7: log ───────────────────────────────────────────────────────
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        env['dynamic.api.log'].log_request(
            endpoint=endpoint,
            method=http_method,
            request_ip=self._get_client_ip(),
            payload_str=raw_body,
            response_code=status,
            response_time_ms=elapsed_ms,
            user=auth_user,
            api_key=api_key_rec,
            query_params=dict(request.httprequest.args) if http_method == 'GET' else None,
        )

        return self._json_response(response_body, status=status,
                                   cors_origins=endpoint.cors_origins)

    # ─────────────────────────────────────────────────────────────────────────
    # Authentication
    # ─────────────────────────────────────────────────────────────────────────

    def _authenticate(self, endpoint, env):
        """
        Returns (user_recordset, api_key_recordset|None).
        Raises an exception with a user-facing message on failure.
        """
        auth_type = endpoint.auth_type

        if auth_type == 'public':
            return env['res.users'].browse(SUPERUSER_ID), None

        if auth_type == 'session':
            # Validate the existing Odoo session
            uid = request.session.uid
            if not uid:
                raise PermissionError('Session authentication required. Please log in to Odoo.')
            user = env['res.users'].browse(uid)
            return user, None

        if auth_type == 'api_key':
            raw_key = request.httprequest.headers.get('X-API-Key', '').strip()
            api_key_rec = env['dynamic.api.key'].validate_key(raw_key, endpoint)
            user = api_key_rec.user_id
            return user, api_key_rec

        raise PermissionError(f'Unknown auth_type: {auth_type}')

    # ─────────────────────────────────────────────────────────────────────────
    # Method handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _handle_get(self, endpoint, env, qs_params):
        """
        GET  /api/dynamic/<slug>            → list records (paginated)
        GET  /api/dynamic/<slug>?id=42      → single record
        GET  /api/dynamic/<slug>?domain=[]  → filtered list (JSON domain)
        """
        model = env[endpoint.model_name].sudo()
        readable_fields = endpoint.get_readable_field_names()
        alias_map = endpoint.get_field_alias_map()

        if not readable_fields:
            return {'success': False, 'data': None,
                    'error': 'No fields configured for this endpoint.', 'meta': {}}, 400

        # Single-record lookup
        record_id = qs_params.get('id')
        if record_id:
            try:
                record_id = int(record_id)
            except ValueError:
                return {'success': False, 'data': None,
                        'error': 'id must be an integer.', 'meta': {}}, 400
            records = model.browse(record_id).exists()
            if not records:
                return {'success': False, 'data': None,
                        'error': f'Record {record_id} not found.', 'meta': {}}, 404
            data = self._serialize_records(records, readable_fields, alias_map)
            return {
                'success': True, 'data': data[0] if data else None,
                'error': None, 'meta': {'method': 'GET', 'id': record_id},
            }, 200

        # List with optional domain
        domain = []
        domain_param = qs_params.get('domain')
        if domain_param:
            try:
                domain = json.loads(domain_param)
                if not isinstance(domain, list):
                    raise ValueError('domain must be a JSON array')
            except (json.JSONDecodeError, ValueError) as e:
                return {'success': False, 'data': None,
                        'error': f'Invalid domain: {e}', 'meta': {}}, 400

        # Pagination
        try:
            page = max(1, int(qs_params.get('page', 1)))
            page_size = min(
                MAX_PAGE_SIZE,
                max(1, int(qs_params.get('page_size', DEFAULT_PAGE_SIZE))),
            )
        except ValueError:
            page, page_size = 1, DEFAULT_PAGE_SIZE

        # Order
        order = qs_params.get('order', 'id asc')
        # Sanitise order to prevent injection: allow only word chars and asc/desc
        import re
        if not re.match(r'^[a-zA-Z0-9_]+(?: (?:asc|desc))?(?:, ?[a-zA-Z0-9_]+(?: (?:asc|desc))?)*$', order, re.I):
            order = 'id asc'

        total = model.search_count(domain)
        offset = (page - 1) * page_size

        records = model.search_read(
            domain=domain,
            fields=readable_fields,
            limit=page_size,
            offset=offset,
            order=order,
        )

        # Apply alias renaming
        data = [
            {alias_map.get(k, k): v for k, v in rec.items() if k in alias_map or k == 'id'}
            for rec in records
        ]

        return {
            'success': True,
            'data': data,
            'error': None,
            'meta': {
                'method': 'GET',
                'total': total,
                'page': page,
                'page_size': page_size,
                'pages': (total + page_size - 1) // page_size if page_size else 1,
            },
        }, 200

    def _handle_post(self, endpoint, env, payload):
        """
        POST /api/dynamic/<slug>   body: {field: value, ...}
        Creates a new record.  Returns the created record's id and readable fields.
        """
        if not endpoint.allow_post:
            return {'success': False, 'data': None,
                    'error': 'POST not enabled for this endpoint.', 'meta': {}}, 405

        writable_fields = endpoint.get_writable_field_names()
        reverse_map = endpoint.get_reverse_alias_map()
        alias_map = endpoint.get_field_alias_map()
        readable_fields = endpoint.get_readable_field_names()

        if not isinstance(payload, dict):
            return {'success': False, 'data': None,
                    'error': 'Request body must be a JSON object.', 'meta': {}}, 400

        # Translate aliases back to field names, filter to writable only
        write_vals = {}
        for key, value in payload.items():
            field_name = reverse_map.get(key, key)
            if field_name in writable_fields:
                write_vals[field_name] = value

        if not write_vals:
            return {'success': False, 'data': None,
                    'error': 'No writable fields found in request body.', 'meta': {}}, 400

        model = env[endpoint.model_name].sudo()
        new_record = model.create(write_vals)

        # Return the new record's data
        raw = new_record.read(readable_fields)[0]
        data = {alias_map.get(k, k): v for k, v in raw.items()}

        return {
            'success': True,
            'data': data,
            'error': None,
            'meta': {'method': 'POST', 'id': new_record.id},
        }, 201

    def _handle_put(self, endpoint, env, payload, qs_params):
        """
        PUT /api/dynamic/<slug>?id=42   body: {field: value, ...}
        Updates an existing record.
        """
        if not endpoint.allow_put:
            return {'success': False, 'data': None,
                    'error': 'PUT not enabled for this endpoint.', 'meta': {}}, 405

        record_id = qs_params.get('id')
        if not record_id:
            return {'success': False, 'data': None,
                    'error': 'Query parameter ?id= is required for PUT.', 'meta': {}}, 400
        try:
            record_id = int(record_id)
        except ValueError:
            return {'success': False, 'data': None,
                    'error': 'id must be an integer.', 'meta': {}}, 400

        writable_fields = endpoint.get_writable_field_names()
        reverse_map = endpoint.get_reverse_alias_map()
        alias_map = endpoint.get_field_alias_map()
        readable_fields = endpoint.get_readable_field_names()

        if not isinstance(payload, dict):
            return {'success': False, 'data': None,
                    'error': 'Request body must be a JSON object.', 'meta': {}}, 400

        write_vals = {}
        for key, value in payload.items():
            field_name = reverse_map.get(key, key)
            if field_name in writable_fields:
                write_vals[field_name] = value

        if not write_vals:
            return {'success': False, 'data': None,
                    'error': 'No writable fields found in request body.', 'meta': {}}, 400

        model = env[endpoint.model_name].sudo()
        record = model.browse(record_id).exists()
        if not record:
            return {'success': False, 'data': None,
                    'error': f'Record {record_id} not found.', 'meta': {}}, 404

        record.write(write_vals)
        raw = record.read(readable_fields)[0]
        data = {alias_map.get(k, k): v for k, v in raw.items()}

        return {
            'success': True,
            'data': data,
            'error': None,
            'meta': {'method': 'PUT', 'id': record_id},
        }, 200

    def _handle_delete(self, endpoint, env, qs_params):
        """
        DELETE /api/dynamic/<slug>?id=42
        Deletes a single record by id.
        """
        if not endpoint.allow_delete:
            return {'success': False, 'data': None,
                    'error': 'DELETE not enabled for this endpoint.', 'meta': {}}, 405

        record_id = qs_params.get('id')
        if not record_id:
            return {'success': False, 'data': None,
                    'error': 'Query parameter ?id= is required for DELETE.', 'meta': {}}, 400
        try:
            record_id = int(record_id)
        except ValueError:
            return {'success': False, 'data': None,
                    'error': 'id must be an integer.', 'meta': {}}, 400

        model = env[endpoint.model_name].sudo()
        record = model.browse(record_id).exists()
        if not record:
            return {'success': False, 'data': None,
                    'error': f'Record {record_id} not found.', 'meta': {}}, 404

        record.unlink()
        return {
            'success': True,
            'data': None,
            'error': None,
            'meta': {'method': 'DELETE', 'id': record_id, 'deleted': True},
        }, 200

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _serialize_records(self, records, field_names, alias_map):
        """
        Convert an ORM recordset to a list of dicts with alias renaming applied.
        Uses read() for efficiency (single SQL call).
        """
        raw_list = records.read(field_names)
        return [
            {alias_map.get(k, k): v for k, v in row.items()}
            for row in raw_list
        ]

    def _get_client_ip(self):
        """Extract the real client IP, respecting X-Forwarded-For."""
        forwarded_for = request.httprequest.headers.get('X-Forwarded-For', '')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.httprequest.remote_addr or 'unknown'

    def _json_response(self, body, status=200, extra_headers=None, cors_origins='*'):
        """Build an HTTP response with JSON body and proper CORS headers."""
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': cors_origins or '*',
            'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, Authorization',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'X-Powered-By': 'Odoo Dynamic REST API',
        }
        if extra_headers:
            headers.update(extra_headers)

        try:
            body_str = json.dumps(body, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            body_str = json.dumps({'success': False, 'data': None,
                                   'error': f'Serialisation error: {e}', 'meta': {}})
            status = 500

        return request.make_response(body_str, headers=list(headers.items()), status=status)

    def _cors_preflight_response(self):
        """Handle OPTIONS pre-flight for CORS."""
        headers = [
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Headers', 'Content-Type, X-API-Key, Authorization'),
            ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
            ('Access-Control-Max-Age', '86400'),
            ('Content-Length', '0'),
        ]
        return request.make_response('', headers=headers, status=204)