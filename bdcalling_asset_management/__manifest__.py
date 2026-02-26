{
    "name": "BDCalling Asset Management",
    "version": "1.0",
    "summary": "Extend assets with product, serial, location & stock value",
    "license": "LGPL-3",
    "author": "BDCalling",

    "depends": [
        "account_asset",
        "stock",
        "stock_account"
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/account_asset_extended_veiws.xml",
        "views/product_template_extended_views.xml",
    ],

    "installable": True,
    "application": False,
}
