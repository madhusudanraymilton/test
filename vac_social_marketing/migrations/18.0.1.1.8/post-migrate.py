# -*- coding: utf-8 -*-
"""
Migration 18.0.1.1.8 - Fix vac.sponsor display order.

Sponsors were originally loaded with noupdate=1, so changing their
sequence values in the XML data file has no effect on existing databases.
This script updates the sequences directly in the database to enforce:

  10 - Chris French
  20 - Stacey Michelon
  30 - Rob Bailey
  40 - VAC
  50 - Webinar
"""
import logging

_logger = logging.getLogger(__name__)

_SPONSOR_SEQUENCES = [
    ('Chris French',    10),
    ('Stacey Michelon', 20),
    ('Rob Bailey',      30),
    ('VAC',             40),
    ('Webinar',         50),
]


def migrate(cr, version):
    for name, seq in _SPONSOR_SEQUENCES:
        cr.execute(
            "UPDATE vac_sponsor SET sequence = %s WHERE name = %s",
            (seq, name),
        )
        _logger.info(
            '[vac_social_marketing] Set vac.sponsor "%s" sequence -> %s',
            name, seq,
        )
