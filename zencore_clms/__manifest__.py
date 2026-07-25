{
    'name': 'Zencore CLMs',
    'version': '19.0.0.1.0',
    'summary': 'Stage-Driven Credit Limit Management System',
    'description': """
        Zencore CLM — Credit Control Engine
        =====================================
        v0.4.0 — Architecture fix release

        BREAKING BUG FIXES in this version:
        ─────────────────────────────────────
        • _compute_clm_balances completely rewritten: old design read
          sale.order.clm_state with bucket values that no longer exist
          after the SRS §4 refactor → all Bucket 1–4 balances were
          permanently 0 → credit freeze never fired.

          New design:
            PI + Bucket 1 : SQL over sale_order_line (undelivered / uninvoiced qty)
            Bucket 2–5    : SQL over account_move.amount_residual,
                            differentiated by clm_customer_acceptance,
                            clm_bank_acceptance, invoice_date_due vs CURRENT_DATE

        • clm_bucket_5_limit / clm_bucket_5_balance fields added to res.partner
          (were referenced in ClmLimitChangeRequest but never declared → AttributeError)

        • account_move_extended_views.xml added to manifest (was missing → no UI
          for Customer Acceptance or Bank Acceptance → Bucket 2→3→4 unreachable)

        • Bank acceptance gate in action_register_payment restored (was commented
          out → SRS §4.3 violation: payments could bypass bank acceptance)

        Other:
        ──────
        • Bucket 5 display added to partner Credit Management tab
        • Bucket 5 aggregation added to parent partner aggregated view
        • clm_bucket_5_limit added to write-protection frozenset
        • SQL constraint added for clm_bucket_5_limit >= 0
        • Daily cron added for automatic Bucket 4 → 5 overdue boundary detection
    """,
    'author': 'Madhusudan Ray',
    'website': 'https://zencoreltd.com',
    'category': 'msa',
    'depends': [
        'base',
        'sale',
        'sale_management',
        'stock',
        'account',
        'contacts',
        'mail',
        'zencore_groups',
        
    ],
    'data': [
        # Security — must be first
        'security/security.xml',
        'security/ir.model.access.csv',

        # Sequences
        'data/ir_sequence_data.xml',

        # Cron — Bucket 5 overdue boundary auto-detection (daily)
        # Without this, Bucket 4→5 transition only occurs when a form is
        # opened (CURRENT_DATE evaluated at compute time). The cron forces
        # daily recompute so overdue exposure surfaces automatically.
        # 'data/clm_cron_data.xml',

        # Views
        'views/res_partner_extended_views.xml',
        'views/sale_order_extended_views.xml',
        'views/account_move_extended_views.xml',
        'views/clm_limit_change_request_views.xml',

        # Reports
        'report/report_commercial_invoice.xml',
        'report/report_proforma_invoice.xml',
        'report/set_delivery_challan.xml',
        'report/report_certificate_of_origin.xml',
        'report/report_beneficiary_certificate.xml',
        'report/report_truck_challan.xml',
        'report/report_packing_list.xml',
        'report/report_lc_document_set.xml',

        # Print menu cleanup — must load AFTER all reports above, and
        # after the `account` module reports it references already exist.
        'data/print_menu_cleanup_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}