# -*- coding: utf-8 -*-
"""
``helpdesk.api.token.blacklist``
================================
Stores the JTI (JWT ID) of every token that has been explicitly revoked
via the logout endpoint.  The ``require_jwt`` decorator checks this table
on every request so revoked tokens are rejected even before their ``exp``
claim would expire.

A scheduled action (cron) provided in ``jwt_config_data.xml`` purges
entries whose ``expires_at`` has passed to keep the table lean.
"""

from odoo import api, fields, models


class HelpdeskApiTokenBlacklist(models.Model):
    _name        = 'helpdesk.api.token.blacklist'
    _description = 'JWT Token Blacklist'
    _order       = 'create_date desc'
    _rec_name    = 'jti'

    # ── Fields ──────────────────────────────────────────────────────────────

    jti = fields.Char(
        string='JWT ID (jti)',
        required=True,
        index=True,
        help='Unique identifier extracted from the JWT payload.',
    )
    uid = fields.Many2one(
        comodel_name='res.users',
        string='Revoked for user',
        ondelete='cascade',
        index=True,
    )
    token_type = fields.Selection(
        selection=[('access', 'Access'), ('refresh', 'Refresh')],
        string='Token type',
        default='access',
    )
    expires_at = fields.Datetime(
        string='Token expiry',
        required=True,
        help='Original exp from the JWT claim. Used for scheduled clean-up.',
    )
    reason = fields.Char(
        string='Revocation reason',
        default='logout',
    )

    # ── Constraints ──────────────────────────────────────────────────────────

    _sql_constraints = [
        ('jti_unique', 'UNIQUE(jti)', 'Each JWT ID must appear only once in the blacklist.'),
    ]

    # ── Class-level helpers (called from jwt_utils) ───────────────────────

    @api.model
    def is_blacklisted(self, jti: str) -> bool:
        """Return ``True`` when *jti* is present in the blacklist."""
        return bool(
            self.sudo().search_count([('jti', '=', jti)], limit=1)
        )

    @api.model
    def revoke(self, jti: str, uid: int, token_type: str,
               expires_at, reason: str = 'logout') -> None:
        """Insert *jti* into the blacklist (idempotent)."""
        if not self.sudo().search([('jti', '=', jti)], limit=1):
            self.sudo().create({
                'jti':        jti,
                'uid':        uid,
                'token_type': token_type,
                'expires_at': expires_at,
                'reason':     reason,
            })

    @api.model
    def purge_expired(self) -> int:
        """
        Delete all blacklist entries whose token has already expired.
        Called by the scheduled cron action.
        Returns the number of records deleted.
        """
        expired = self.sudo().search(
            [('expires_at', '<', fields.Datetime.now())]
        )
        count = len(expired)
        expired.unlink()
        return count
