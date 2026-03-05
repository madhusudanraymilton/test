{
    "name": "Systech Publications",
    "version": "19.0.1.0.0",
    "category": "Contacts",
    "summary": "Add Thana & District with full search/group support",
    "author": "Your Company",
    "depends": [
        "base",
        "contacts",
        "sale",
        "account",
        "stock"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_extended_views.xml",
        "views/res_district_views.xml",
        "views/res_thana_views.xml",
        'views/sale_order_extended_views.xml',
        'views/account_move_extended_views.xml',
        'views/stock_picking_extended_views.xml',
        # "views/sale_order_views.xml",
        # "views/account_move_views.xml",
        # "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}