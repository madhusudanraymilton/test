# -*- coding: utf-8 -*-
"""
Post-install / post-upgrade hook:
Assign the first social lead stage (by sequence) to every social lead
that currently has social_stage_id = False (null).
This covers leads created before the default was introduced.
"""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    _backfill_social_stage(env)


def post_migrate_hook(env):
    _backfill_social_stage(env)


def _backfill_social_stage(env):
    first_stage = env['vac.social.lead.stage'].search(
        [], order='sequence, name', limit=1)

    if not first_stage:
        _logger.warning(
            '[vac_social_marketing] No social lead stages found — '
            'skipping social_stage_id backfill.'
        )
        return

    leads = env['vac.event.lead'].search([
        '|', '|', '|',
            ('social_fb_id', '!=', False),
            ('social_ig_id', '!=', False),
            ('social_office_id', '!=', False),
            ('platform', 'in', ['facebook', 'instagram', 'office']),
        ('social_stage_id', '=', False),
    ])

    if leads:
        leads.write({'social_stage_id': first_stage.id})
        _logger.info(
            '[vac_social_marketing] Backfilled social_stage_id=%s (%s) '
            'on %d social lead(s).',
            first_stage.id, first_stage.name, len(leads),
        )
    else:
        _logger.info(
            '[vac_social_marketing] No social leads needed backfill.'
        )
