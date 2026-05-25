#!/usr/bin/env python3
"""
prune_addons.py
---------------
Strip Odoo's bundled /usr/lib/python3/dist-packages/odoo/addons folder so that
only the modules in WHITELIST remain on disk. Run at image build time.

The whitelist is the minimal closure required to install the HR app:

  Core / framework
    base, web, base_setup

  Web / UI / bus / routing framework
    bus, web_tour, web_editor, http_routing

  HR dependency tree (hr -> base_setup, mail, resource, digest)
    mail, resource, digest, portal, hr

Anything not in WHITELIST is physically deleted, so it can never appear in
the Apps menu, even in developer mode.
"""

from __future__ import annotations

import os
import shutil
import sys

ADDONS_DIR = "/usr/lib/python3/dist-packages/odoo/addons"

WHITELIST: set[str] = {
    # Core / framework (required to boot Odoo)
    "base",
    "web",
    "base_setup",
    "base_install",
    "base_import_module",
    "base_import",
    "base_automation",
    "base_geolocalize",
    "base_sparse_field",
    "base_vat",

    # Web / framework helpers
    "bus",
    "web_tour",
    "web_editor",
    "http_routing",

    # HR dependency closure
    "mail",
    "mail_bot",
    "mail_plugin",
    "mail_bot_hr",

    "resource",
    "digest",
    "portal",
    "hr",
    "hr_fleet",
    "hr_skills",
    "hr_expense",
    "hr_calendar",
    "hr_holidays",
    "hr_livechat",
    "hr_presence",
    "hr_org_chart",
    "hr_timesheet",
    "hr_attendance",
    "hr_work_entry",
    "hr_homeworking",
    "contacts",
    "http_routing",
    "l10n_us",
    "html_editor",
    "utm",
    "barcodes",
}


def main() -> int:
    if not os.path.isdir(ADDONS_DIR):
        print(f"[prune_addons] ERROR: {ADDONS_DIR} not found", file=sys.stderr)
        return 1

    kept: list[str] = []
    removed: list[str] = []

    for entry in sorted(os.listdir(ADDONS_DIR)):
        full = os.path.join(ADDONS_DIR, entry)

        if not os.path.isdir(full):
            continue

        if entry in WHITELIST:
            kept.append(entry)
        else:
            shutil.rmtree(full, ignore_errors=True)
            removed.append(entry)

    print(f"[prune_addons] Kept ({len(kept)}): {', '.join(kept)}")
    print(f"[prune_addons] Removed ({len(removed)}) modules from bundled addons.")

    # Sanity check: every whitelisted module must still exist
    missing = [
        module
        for module in WHITELIST
        if not os.path.isdir(os.path.join(ADDONS_DIR, module))
    ]

    if missing:
        print(
            f"[prune_addons] WARNING: whitelisted modules not present on disk: {missing}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
