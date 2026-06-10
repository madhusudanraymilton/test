# {
#     'name': 'Zencore CLMs',
#     'version': '19.0.0.3.0',
#     'summary': 'Stage-Driven Credit Limit Management System',
#     'description': """
#         Zencore CLM — Credit Control Engine
#         =====================================
#         v0.3.0 — Production-hardened release
#         - Stage-driven exposure tracking (PI → Bucket 1-4 → Paid)
#         - Real-time computed balances per bucket (read_group optimised)
#         - Automatic credit freeze on limit breach
#         - Group-level freeze propagation (all children blocked if any frozen)
#         - CCM → Finance Manager approval workflow for limit changes
#         - Full audit trail with chatter on every stage transition
#         - SoD enforcement: Salesperson / Sales Manager / CCM / Warehouse / TDO / Finance
#         - Reconciliation-safe payment detection hook
#     """,
#     'author': 'Zencore',
#     'website': 'https://zencoreltd.com',
#     'category': 'msa',
#     'depends': [
#         'base',
#         'sale',
#         'sale_management',
#         'stock',
#         'account',
#         'contacts',
#         'mail',
#         'zencore_groups',
#     ],
#     'data': [
#         # Security — must be first
#         'security/security.xml',
#         'security/ir.model.access.csv',
#         # Sequences
#         'data/ir_sequence_data.xml',
#         # Views
#         'views/res_partner_extended_views.xml',
#         'views/sale_order_extended_views.xml',
#         'views/clm_limit_change_request_views.xml',
#         "views/account_move_extended_views.xml",
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }


# # """
# # id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink

# # access_clm_lcr_ccm,clm lcr ccm,model_clm_limit_change_request,zencore_clms.group_zencore_clm_ccm,1,1,1,0
# # access_clm_lcr_finance,clm lcr finance,model_clm_limit_change_request,zencore_clms.group_zencore_clm_finance,1,1,0,0
# # access_clm_lcr_sales_manager,clm lcr sales manager,model_clm_limit_change_request,zencore_clms.group_zencore_clm_sales_manager,1,0,0,0

# # access_sale_order_salesperson,sale order salesperson,sale.model_sale_order,zencore_clms.group_zencore_clm_salesperson,1,1,1,0
# # access_sale_order_sales_manager,sale order sales manager,sale.model_sale_order,zencore_clms.group_zencore_clm_sales_manager,1,1,0,0
# # access_sale_order_ccm,sale order ccm,sale.model_sale_order,zencore_clms.group_zencore_clm_ccm,1,1,0,0
# # access_sale_order_finance,sale order finance,sale.model_sale_order,zencore_clms.group_zencore_clm_finance,1,0,0,0
# # access_sale_order_tdo,sale order tdo,sale.model_sale_order,zencore_clms.group_zencore_clm_tdo,1,0,0,0

# # access_account_move_tdo,account move tdo,account.model_account_move,zencore_clms.group_zencore_clm_tdo,1,1,1,0
# # access_account_move_finance,account move finance,account.model_account_move,zencore_clms.group_zencore_clm_finance,1,1,0,0
# # access_account_move_ccm,account move ccm,account.model_account_move,zencore_clms.group_zencore_clm_ccm,1,0,0,0

# # access_res_partner_ccm,res partner ccm,base.model_res_partner,zencore_clms.group_zencore_clm_ccm,1,1,0,0
# # access_res_partner_finance,res partner finance,base.model_res_partner,zencore_clms.group_zencore_clm_finance,1,0,0,0
# # access_res_partner_sales_manager,res partner sales manager,base.model_res_partner,zencore_clms.group_zencore_clm_sales_manager,1,0,0,0

# # access_stock_picking_warehouse,stock picking warehouse,stock.model_stock_picking,zencore_clms.group_zencore_clm_warehouse,1,1,0,0
# # access_stock_picking_finance,stock picking finance,stock.model_stock_picking,zencore_clms.group_zencore_clm_finance,1,0,0,0
# # access_stock_picking_ccm,stock picking ccm,stock.model_stock_picking,zencore_clms.group_zencore_clm_ccm,1,0,0,0
# # access_stock_picking_sales_manager,stock picking sales manager,stock.model_stock_picking,zencore_clms.group_zencore_clm_sales_manager,1,0,0,0
# # access_stock_picking_salesperson,stock picking salesperson,stock.model_stock_picking,zencore_clms.group_zencore_clm_salesperson,1,0,0,0
# # access_stock_picking_tdo,stock picking tdo,stock.model_stock_picking,zencore_clms.group_zencore_clm_tdo,1,0,0,0

# # """

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
        # BUG 3 FIX: this file was entirely absent — no UI for Customer/Bank
        # Acceptance on invoices, making Bucket 2→3→4 transitions unreachable.
        'views/account_move_extended_views.xml',
        'views/clm_limit_change_request_views.xml',
        
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}