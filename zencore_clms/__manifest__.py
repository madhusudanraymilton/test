{
    'name': 'Zencore CLMs',
    'version': '19.0.0.3.0',
    'summary': 'Stage-Driven Credit Limit Management System',
    'description': """
        Zencore CLM — Credit Control Engine
        =====================================
        v0.3.0 — Production-hardened release
        - Stage-driven exposure tracking (PI → Bucket 1-4 → Paid)
        - Real-time computed balances per bucket (read_group optimised)
        - Automatic credit freeze on limit breach
        - Group-level freeze propagation (all children blocked if any frozen)
        - CCM → Finance Manager approval workflow for limit changes
        - Full audit trail with chatter on every stage transition
        - SoD enforcement: Salesperson / Sales Manager / CCM / Warehouse / TDO / Finance
        - Reconciliation-safe payment detection hook
    """,
    'author': 'Zencore',
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
        # Views
        'views/res_partner_extended_views.xml',
        'views/sale_order_extended_views.xml',
        'views/clm_limit_change_request_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}


# """
# id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink

# access_clm_lcr_ccm,clm lcr ccm,model_clm_limit_change_request,zencore_clms.group_zencore_clm_ccm,1,1,1,0
# access_clm_lcr_finance,clm lcr finance,model_clm_limit_change_request,zencore_clms.group_zencore_clm_finance,1,1,0,0
# access_clm_lcr_sales_manager,clm lcr sales manager,model_clm_limit_change_request,zencore_clms.group_zencore_clm_sales_manager,1,0,0,0

# access_sale_order_salesperson,sale order salesperson,sale.model_sale_order,zencore_clms.group_zencore_clm_salesperson,1,1,1,0
# access_sale_order_sales_manager,sale order sales manager,sale.model_sale_order,zencore_clms.group_zencore_clm_sales_manager,1,1,0,0
# access_sale_order_ccm,sale order ccm,sale.model_sale_order,zencore_clms.group_zencore_clm_ccm,1,1,0,0
# access_sale_order_finance,sale order finance,sale.model_sale_order,zencore_clms.group_zencore_clm_finance,1,0,0,0
# access_sale_order_tdo,sale order tdo,sale.model_sale_order,zencore_clms.group_zencore_clm_tdo,1,0,0,0

# access_account_move_tdo,account move tdo,account.model_account_move,zencore_clms.group_zencore_clm_tdo,1,1,1,0
# access_account_move_finance,account move finance,account.model_account_move,zencore_clms.group_zencore_clm_finance,1,1,0,0
# access_account_move_ccm,account move ccm,account.model_account_move,zencore_clms.group_zencore_clm_ccm,1,0,0,0

# access_res_partner_ccm,res partner ccm,base.model_res_partner,zencore_clms.group_zencore_clm_ccm,1,1,0,0
# access_res_partner_finance,res partner finance,base.model_res_partner,zencore_clms.group_zencore_clm_finance,1,0,0,0
# access_res_partner_sales_manager,res partner sales manager,base.model_res_partner,zencore_clms.group_zencore_clm_sales_manager,1,0,0,0

# access_stock_picking_warehouse,stock picking warehouse,stock.model_stock_picking,zencore_clms.group_zencore_clm_warehouse,1,1,0,0
# access_stock_picking_finance,stock picking finance,stock.model_stock_picking,zencore_clms.group_zencore_clm_finance,1,0,0,0
# access_stock_picking_ccm,stock picking ccm,stock.model_stock_picking,zencore_clms.group_zencore_clm_ccm,1,0,0,0
# access_stock_picking_sales_manager,stock picking sales manager,stock.model_stock_picking,zencore_clms.group_zencore_clm_sales_manager,1,0,0,0
# access_stock_picking_salesperson,stock picking salesperson,stock.model_stock_picking,zencore_clms.group_zencore_clm_salesperson,1,0,0,0
# access_stock_picking_tdo,stock picking tdo,stock.model_stock_picking,zencore_clms.group_zencore_clm_tdo,1,0,0,0

# """