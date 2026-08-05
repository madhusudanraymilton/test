# -*- coding: utf-8 -*-
"""
Migration 18.0.1.1.7 – Add columns that vac.social.mixin introduced
but that were never materialised in the vac_social_fb / vac_social_ing
tables (the DB was created before those fields were added to the mixin).

Root cause of the reported error:
    psycopg2.errors.UndefinedColumn:
        column vac_social_fb.stage_id does not exist

We add every column that the mixin now owns so that Odoo's ORM can read
and write all of them without hitting UndefinedColumn errors.

Only columns that do not already exist are created, so running this
script more than once (or against a fresh install) is perfectly safe.
"""
import logging

_logger = logging.getLogger(__name__)

# ── tables that inherit vac.social.mixin ─────────────────────────────────────
_TABLES = ('vac_social_fb', 'vac_social_ing')

# ── DDL for each potentially-missing column ───────────────────────────────────
# Format: (column_name, SQL_type_definition)
_COLUMNS = [
    # Many2one FK → vac_event_stage (stage_id)
    ('stage_id',                   'INTEGER'),
    # stored-computed slug (Char)
    ('slug',                       'VARCHAR'),
    # stored-computed qr_code (Binary → bytea)
    ('qr_code',                    'BYTEA'),
    # badge_background_filename (Char) – the binary itself is in ir.attachment
    ('badge_background_filename',  'VARCHAR'),
]


def migrate(cr, version):
    for table in _TABLES:
        # Safety check – skip tables that don't exist yet (fresh installs let
        # Odoo create them with the correct schema via the normal ORM path).
        cr.execute(
            "SELECT to_regclass(%s)",
            (table,),
        )
        if cr.fetchone()[0] is None:
            _logger.info(
                '[vac_social_marketing] Table %s does not exist yet – '
                'skipping (fresh install will create it correctly).',
                table,
            )
            continue

        for col, col_type in _COLUMNS:
            cr.execute(
                """
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_name  = %s
                   AND column_name = %s
                """,
                (table, col),
            )
            if cr.fetchone():
                _logger.debug(
                    '[vac_social_marketing] %s.%s already exists – skipping.',
                    table, col,
                )
                continue

            cr.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{col}" {col_type}'
            )
            _logger.info(
                '[vac_social_marketing] Added column %s.%s (%s).',
                table, col, col_type,
            )
