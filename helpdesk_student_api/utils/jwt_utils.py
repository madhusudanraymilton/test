# -*- coding: utf-8 -*-
"""
JWT utility layer for the Helpdesk Student REST API.

Responsibilities
----------------
- Secret key:  auto-generated once, persisted in ``ir.config_parameter``
- Token generation:  ``generate_tokens(uid, env)`` → (access_token, refresh_token)
- Token validation: ``decode_token(raw, env)`` → payload dict or raises
- Helpers:  ``datetime`` ↔ epoch conversion

Requires
--------
    pip install PyJWT>=2.0

All token operations use  HS256  (HMAC-SHA256).

Token payload shape
-------------------
{
    "uid":        5,                          # Odoo user id
    "email":      "student@university.com",
    "partner_id": 12,
    "name":       "John Smith",
    "type":       "access",                   # or "refresh"
    "jti":        "550e8400-e29b-41d4…",      # uuid4, unique per token
    "iat":        1710000000,                 # issued-at  (epoch)
    "exp":        1710003600,                 # expires-at (epoch)
}
"""

import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── System-parameter keys ────────────────────────────────────────────────────
_PARAM_SECRET         = 'helpdesk_api.jwt_secret'
_PARAM_ACCESS_TTL     = 'helpdesk_api.jwt_access_ttl_minutes'
_PARAM_REFRESH_TTL    = 'helpdesk_api.jwt_refresh_ttl_days'

# ── Defaults (overridable via Settings → Technical → System Parameters) ───────
_DEFAULT_ACCESS_TTL   = 60          # minutes  →  1 hour
_DEFAULT_REFRESH_TTL  = 7           # days     →  7 days


# ---------------------------------------------------------------------------
# Lazy JWT import — gives a clear error if PyJWT is missing
# ---------------------------------------------------------------------------

def _jwt():
    try:
        import jwt as _jwt_lib
        return _jwt_lib
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            'PyJWT is required.  Install it with:  pip install PyJWT>=2.0'
        ) from exc


# ---------------------------------------------------------------------------
# Secret key management
# ---------------------------------------------------------------------------

def _get_secret(env) -> str:
    """
    Return the JWT HS256 secret key, creating and persisting a fresh
    cryptographically random one if it does not yet exist.

    The secret is stored in ``ir.config_parameter`` under the key
    ``helpdesk_api.jwt_secret``.  It is never exposed via any API endpoint.
    """
    IrParam = env['ir.config_parameter'].sudo()
    secret  = IrParam.get_param(_PARAM_SECRET)

    if not secret:
        secret = secrets.token_urlsafe(64)          # 512 bits, URL-safe base64
        IrParam.set_param(_PARAM_SECRET, secret)
        _logger.info('JWT: new secret key generated and persisted.')

    return secret


def rotate_secret(env) -> str:
    """
    Generate a new secret key and persist it, **immediately invalidating
    all currently issued tokens**.  Call this only when a full token
    revocation is intentional (e.g. security incident).
    """
    IrParam = env['ir.config_parameter'].sudo()
    new_secret = secrets.token_urlsafe(64)
    IrParam.set_param(_PARAM_SECRET, new_secret)
    _logger.warning('JWT: secret key rotated — all existing tokens are now invalid.')
    return new_secret


# ---------------------------------------------------------------------------
# TTL helpers
# ---------------------------------------------------------------------------

def _access_ttl(env) -> timedelta:
    minutes = int(
        env['ir.config_parameter'].sudo()
        .get_param(_PARAM_ACCESS_TTL, _DEFAULT_ACCESS_TTL)
    )
    return timedelta(minutes=minutes)


def _refresh_ttl(env) -> timedelta:
    days = int(
        env['ir.config_parameter'].sudo()
        .get_param(_PARAM_REFRESH_TTL, _DEFAULT_REFRESH_TTL)
    )
    return timedelta(days=days)


# ---------------------------------------------------------------------------
# Token generation
# ---------------------------------------------------------------------------

def _build_payload(user, token_type: str, ttl: timedelta) -> dict:
    """Construct a signed JWT payload dict (not yet encoded)."""
    now = datetime.now(tz=timezone.utc)
    return {
        'uid':        user.id,
        'email':      user.email or user.partner_id.email or '',
        'partner_id': user.partner_id.id,
        'name':       user.name,
        'type':       token_type,
        'jti':        str(uuid.uuid4()),
        'iat':        int(now.timestamp()),
        'exp':        int((now + ttl).timestamp()),
    }


def generate_tokens(uid: int, env) -> dict:
    """
    Generate a fresh **(access_token, refresh_token)** pair for *uid*.

    Returns a dict::

        {
            "access_token":       "<jwt>",
            "refresh_token":      "<jwt>",
            "token_type":         "Bearer",
            "expires_in":         3600,          # access TTL in seconds
            "refresh_expires_in": 604800,        # refresh TTL in seconds
        }
    """
    jwt     = _jwt()
    user    = env['res.users'].sudo().browse(uid)
    secret  = _get_secret(env)
    a_ttl   = _access_ttl(env)
    r_ttl   = _refresh_ttl(env)

    access_payload  = _build_payload(user, 'access',  a_ttl)
    refresh_payload = _build_payload(user, 'refresh', r_ttl)

    access_token  = jwt.encode(access_payload,  secret, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, secret, algorithm='HS256')

    return {
        'access_token':       access_token,
        'refresh_token':      refresh_token,
        'token_type':         'Bearer',
        'expires_in':         int(a_ttl.total_seconds()),
        'refresh_expires_in': int(r_ttl.total_seconds()),
    }


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

class JWTError(Exception):
    """Raised when a token cannot be validated.  ``code`` maps to API error."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code    = code
        self.message = message


def decode_token(raw_token: str, env, *, expected_type: str = 'access') -> dict:
    """
    Decode and fully validate *raw_token*.

    Checks performed (in order):
    1. Structural / cryptographic validity  (PyJWT)
    2. Expiry  (``exp`` claim)
    3. ``type`` claim matches *expected_type*
    4. JTI is not in the blacklist table

    Returns the decoded payload dict on success.
    Raises :class:`JWTError` on any failure.
    """
    jwt    = _jwt()
    secret = _get_secret(env)

    try:
        payload = jwt.decode(
            raw_token,
            secret,
            algorithms=['HS256'],
            options={'require': ['exp', 'iat', 'jti', 'uid', 'type']},
        )
    except jwt.ExpiredSignatureError:
        raise JWTError('TOKEN_EXPIRED', 'Token has expired. Please log in again.')
    except jwt.InvalidTokenError as exc:
        raise JWTError('INVALID_TOKEN', f'Token is invalid: {exc}')

    # ── type check ────────────────────────────────────────────────────────
    if payload.get('type') != expected_type:
        raise JWTError(
            'WRONG_TOKEN_TYPE',
            f'Expected a {expected_type} token, got {payload.get("type")!r}.',
        )

    # ── blacklist check ───────────────────────────────────────────────────
    jti = payload.get('jti', '')
    if env['helpdesk.api.token.blacklist'].sudo().is_blacklisted(jti):
        raise JWTError('TOKEN_REVOKED', 'Token has been revoked. Please log in again.')

    return payload


# ---------------------------------------------------------------------------
# Convenience: epoch → datetime
# ---------------------------------------------------------------------------

def epoch_to_datetime(epoch: int) -> datetime:
    """Convert a Unix timestamp (int) to a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(epoch, tz=timezone.utc)
