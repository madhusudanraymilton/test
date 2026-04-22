# -*- coding: utf-8 -*-
"""
Helpdesk Student REST API — Authentication Controller
======================================================

ROOT CAUSES OF EMPTY RESPONSE IN ODOO 19
-----------------------------------------

1. res.users._login() is NOT the right API with auth='none'
   ─────────────────────────────────────────────────────────
   With auth='none', request.env uses an environment with no real user context.
   Calling _login() on it can raise unexpected errors (AccessDenied, ValueError,
   or just crash silently) because the ORM cursor state differs from a normal
   authenticated request.

   FIX → Use odoo.service.common.authenticate(db, login, password, {})
   This is the stable public API used by /web/session/authenticate since Odoo 8.
   It is version-stable, handles cursor management internally, and returns uid
   on success or raises AccessDenied.

2. Unhandled exceptions produce an empty HTTP body (not JSON)
   ────────────────────────────────────────────────────────────
   When a type='http' route raises an unhandled exception, Odoo 19's HTTP layer
   does NOT convert it to a JSON error — it logs it and may return an empty body,
   an HTML error page, or a 500 with no content-type. curl sees 0 bytes, python3
   -m json.tool says "Expecting value: line 1 column 1 (char 0)".

   FIX → Wrap the ENTIRE handler (including imports) in a broad try/except that
   ALWAYS returns a valid JSON Response, even for totally unexpected errors.

3. request.env.cr.dbname can raise AttributeError with auth='none'
   ─────────────────────────────────────────────────────────────────
   FIX → Use request.db (the db name set by Odoo's dispatcher before the handler
   runs). This is always set, even with auth='none'.

4. Uncaught ImportError when PyJWT is not installed
   ──────────────────────────────────────────────────
   If PyJWT is missing the lazy _jwt() call raises RuntimeError which escapes
   try/except blocks placed only inside handler logic.

   FIX → Catch at the outermost level + emit a clear error message.

HOW TO DEBUG AN EMPTY RESPONSE
───────────────────────────────
# 1. See raw response (bypasses json.tool)
curl -s -X POST http://localhost:8019/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","password":"123"}'

# 2. See HTTP status + headers
curl -i -X POST http://localhost:8019/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"a@b.com","password":"123"}'

# 3. Health check (no auth, no db) — if this returns JSON, routing is OK
curl -s http://localhost:8019/api/v1/health

# 4. Check Odoo logs
tail -f /var/log/odoo/odoo.log | grep -E "(ERROR|helpdesk|auth)"
"""

import json
import logging

from odoo.http import request, route, Controller, Response

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Universal safe response helpers (no external imports needed)
# ---------------------------------------------------------------------------

def _ok(data: dict, meta: dict = None) -> Response:
    payload = {'status': 'success', 'data': data}
    if meta:
        payload['meta'] = meta
    return Response(
        json.dumps(payload, default=str),
        status=200,
        content_type='application/json; charset=utf-8',
    )


def _err(http_status: int, code: str, message: str) -> Response:
    return Response(
        json.dumps({'status': 'error', 'error': {'code': code, 'message': message}}),
        status=http_status,
        content_type='application/json; charset=utf-8',
    )


# ---------------------------------------------------------------------------
# Body parser — merges all possible input sources
# ---------------------------------------------------------------------------

def _get_body(**odoo_kwargs) -> dict:
    """
    Merge POST data from every possible source.

    Priority (highest wins): JSON body > odoo_kwargs (form-encoded) > query string

    Why all three sources:
    - application/json   → axios, fetch, curl -H 'Content-Type: application/json'
    - form-encoded       → Odoo parses this into **kwargs automatically
    - query string       → some testing tools send params in the URL even for POST
    """
    httpreq = request.httprequest

    # Lowest priority: URL query string
    merged = {k: v for k, v in httpreq.args.items()}

    # Mid priority: Odoo-parsed form/multipart kwargs
    # Odoo already ran Werkzeug's form parser before our handler was called.
    # Filter out framework-internal keys (they start with underscore).
    for key, val in odoo_kwargs.items():
        if not key.startswith('_'):
            merged[key] = val[0] if isinstance(val, list) else val

    # Highest priority: raw JSON body
    # get_data(cache=True) always works even after Werkzeug consumed the stream
    # for form parsing (Werkzeug caches it internally).
    try:
        raw = httpreq.get_data(cache=True)
        if raw:
            parsed = json.loads(raw.decode('utf-8'))
            if isinstance(parsed, dict):
                merged.update(parsed)
    except (ValueError, UnicodeDecodeError):
        pass  # not JSON — form data already captured above

    _logger.debug('_get_body result keys: %s', list(merged.keys()))
    return merged


# ---------------------------------------------------------------------------
# Stable Odoo 19 authentication helper
# ---------------------------------------------------------------------------

def _authenticate(db: str, login: str, password: str) -> int | None:
    """
    Authenticate *login* / *password* against *db* and return the uid.

    Uses ``odoo.service.common.authenticate`` — the stable public RPC API
    that works identically across Odoo 15–19 and handles its own cursor /
    transaction management correctly.

    Returns uid (int) on success, None on failure.
    """
    try:
        # This is the exact same call as /web/session/authenticate JSON-RPC.
        # It is safe to call from any context, including auth='none' routes.
        from odoo.service.common import authenticate as odoo_authenticate
        uid = odoo_authenticate(db, login, password, {})
        return uid if uid else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class HelpdeskAuthController(Controller):

    # -----------------------------------------------------------------------
    # HEALTH CHECK  ─  GET /api/v1/health
    # (no auth, no DB ops — use this to verify routing works)
    # -----------------------------------------------------------------------

    @route(
        '/api/v1/health',
        type='http',
        auth='none',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def health(self, **_kwargs):
        """Quick smoke-test. If this returns JSON, routing is working."""
        return _ok({'message': 'Helpdesk Student API is running.'})

    # -----------------------------------------------------------------------
    # 1. LOGIN  ─  POST /api/v1/auth/login
    # -----------------------------------------------------------------------

    @route(
        '/api/v1/auth/login',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def login(self, **kwargs):
        """
        Authenticate a student and issue JWT access + refresh tokens.

        Accepts JSON body, form-encoded body, or query-string params.

        Request body (any of the following formats work)
        -------------------------------------------------
        JSON:          {"email": "a@uni.com", "password": "secret"}
        Form-encoded:  email=a@uni.com&password=secret

        Success 200
        -----------
        {
            "status": "success",
            "data": {
                "access_token":       "<jwt>",
                "refresh_token":      "<jwt>",
                "token_type":         "Bearer",
                "expires_in":         3600,
                "refresh_expires_in": 604800,
                "user": {
                    "uid": 5, "name": "...", "email": "...", "partner_id": 12
                }
            }
        }
        """
        try:
            # ── 1. Parse body ────────────────────────────────────────────
            body     = _get_body(**kwargs)
            email    = (body.get('email')    or '').strip()
            password = (body.get('password') or '').strip()

            _logger.info(
                'LOGIN attempt: email=%r, password_provided=%s, body_keys=%s',
                email, bool(password), list(body.keys()),
            )

            if not email or not password:
                return _err(400, 'MISSING_FIELDS',
                            'Both "email" and "password" are required.')

            # ── 2. Resolve db name safely ────────────────────────────────
            # request.db is always set by Odoo's dispatcher before the handler.
            # request.env.cr.dbname can raise AttributeError with auth='none'.
            db = request.db
            if not db:
                _logger.error('No database name available on request')
                return _err(500, 'INTERNAL_ERROR', 'Database not configured.')

            # ── 3. Authenticate — try email as login, then as partner email
            uid = _authenticate(db, email, password)

            if not uid:
                # Fallback: email might be partner.email while login is different
                # (e.g. user created via portal where login = email, but let's check)
                user_rec = (
                    request.env['res.users']
                    .sudo()
                    .search([
                        ('partner_id.email', '=ilike', email),
                        ('active', '=', True),
                    ], limit=1)
                )
                if user_rec and user_rec.login != email:
                    uid = _authenticate(db, user_rec.login, password)

            if not uid:
                _logger.warning('LOGIN FAILED: email=%s', email)
                return _err(401, 'INVALID_CREDENTIALS',
                            'Invalid email or password.')

            # ── 4. Import JWT helpers (catches missing PyJWT clearly) ────
            try:
                from ..utils.jwt_utils import generate_tokens
            except RuntimeError as exc:
                _logger.error('JWT dependency error: %s', exc)
                return _err(500, 'DEPENDENCY_ERROR', str(exc))

            # ── 5. Issue tokens ──────────────────────────────────────────
            token_data = generate_tokens(uid, request.env)
            user       = request.env['res.users'].sudo().browse(uid)
            token_data['user'] = {
                'uid':        user.id,
                'name':       user.name,
                'email':      user.email or user.partner_id.email or '',
                'partner_id': user.partner_id.id,
            }

            _logger.info('LOGIN OK: uid=%s email=%s', uid, email)
            return _ok(token_data)

        except Exception as exc:
            # Catch-all: ALWAYS return JSON, never let an exception produce
            # an empty response.
            _logger.exception('UNHANDLED error in login: %s', exc)
            return _err(500, 'INTERNAL_ERROR',
                        f'An unexpected error occurred: {type(exc).__name__}: {exc}')

    # -----------------------------------------------------------------------
    # 2. REFRESH  ─  POST /api/v1/auth/refresh
    # -----------------------------------------------------------------------

    @route(
        '/api/v1/auth/refresh',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def refresh(self, **kwargs):
        """
        Exchange a refresh token for a new access + refresh token pair.
        The old refresh token is immediately blacklisted (rotation).

        Body: { "refresh_token": "<jwt>" }
        """
        try:
            from ..utils.jwt_utils import JWTError, decode_token, epoch_to_datetime, generate_tokens

            body        = _get_body(**kwargs)
            raw_refresh = (body.get('refresh_token') or '').strip()

            if not raw_refresh:
                return _err(400, 'MISSING_FIELDS',
                            '"refresh_token" is required.')

            try:
                payload = decode_token(raw_refresh, request.env, expected_type='refresh')
            except JWTError as exc:
                return _err(401, exc.code, exc.message)

            uid = payload['uid']
            jti = payload['jti']
            exp = payload['exp']

            # Rotate: blacklist old refresh token before issuing new pair
            request.env['helpdesk.api.token.blacklist'].sudo().revoke(
                jti=jti, uid=uid, token_type='refresh',
                expires_at=epoch_to_datetime(exp), reason='token_rotation',
            )

            token_data = generate_tokens(uid, request.env)
            _logger.info('REFRESH OK: uid=%s old_jti=%s', uid, jti)
            return _ok(token_data)

        except Exception as exc:
            _logger.exception('UNHANDLED error in refresh: %s', exc)
            return _err(500, 'INTERNAL_ERROR',
                        f'An unexpected error occurred: {type(exc).__name__}: {exc}')

    # -----------------------------------------------------------------------
    # 3. LOGOUT  ─  POST /api/v1/auth/logout
    # -----------------------------------------------------------------------

    @route(
        '/api/v1/auth/logout',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def logout(self, **kwargs):
        """
        Revoke the current access token (and optionally the refresh token).

        Headers: Authorization: Bearer <access_token>
        Body:    { "refresh_token": "<jwt>" }  (optional)
        """
        try:
            from ..utils.jwt_utils import JWTError, decode_token, epoch_to_datetime

            auth_header = request.httprequest.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return _err(401, 'MISSING_AUTH',
                            'Authorization: Bearer <access_token> header required.')

            raw_access = auth_header[len('Bearer '):]

            # Decode with verify_exp=False — allow revoking already-expired tokens
            try:
                import jwt as _jwt
                secret = (
                    request.env['ir.config_parameter']
                    .sudo()
                    .get_param('helpdesk_api.jwt_secret', '')
                )
                payload = _jwt.decode(
                    raw_access, secret, algorithms=['HS256'],
                    options={'require': ['jti', 'uid', 'type', 'exp'],
                             'verify_exp': False},
                )
            except Exception as exc:
                return _err(401, 'INVALID_TOKEN', f'Token is invalid: {exc}')

            uid = payload.get('uid')
            jti = payload.get('jti')
            exp = payload.get('exp')

            if jti:
                request.env['helpdesk.api.token.blacklist'].sudo().revoke(
                    jti=jti, uid=uid, token_type='access',
                    expires_at=epoch_to_datetime(exp), reason='logout',
                )

            # Best-effort: also revoke refresh token if provided
            body        = _get_body(**kwargs)
            raw_refresh = (body.get('refresh_token') or '').strip()
            if raw_refresh:
                try:
                    rp = decode_token(raw_refresh, request.env, expected_type='refresh')
                    request.env['helpdesk.api.token.blacklist'].sudo().revoke(
                        jti=rp['jti'], uid=rp['uid'], token_type='refresh',
                        expires_at=epoch_to_datetime(rp['exp']), reason='logout',
                    )
                except JWTError:
                    pass

            _logger.info('LOGOUT OK: uid=%s jti=%s', uid, jti)
            return _ok({'message': 'Logged out successfully.'})

        except Exception as exc:
            _logger.exception('UNHANDLED error in logout: %s', exc)
            return _err(500, 'INTERNAL_ERROR',
                        f'An unexpected error occurred: {type(exc).__name__}: {exc}')
