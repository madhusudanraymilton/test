# -*- coding: utf-8 -*-
#╔══════════════════════════════════════════════════════════════════════╗
#║                                                                      ║
#║                  ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                   ║
#║                  ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                   ║
#║                  ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                   ║
#║                  ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                   ║
#║                  ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                   ║
#║                  ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                   ║
#║                            ╔═╝║     ╔═╝║                             ║
#║                            ╚══╝     ╚══╝                             ║
#║                  SOFTWARE DEVELOPED AND SUPPORTED BY                 ║
#║                ALMIGHTY CONSULTING SOLUTIONS PVT. LTD.               ║
#║                      COPYRIGHT (C) 2016 - TODAY                      ║
#║                      https://www.almightycs.com                      ║
#║                                                                      ║
#╚══════════════════════════════════════════════════════════════════════╝
{
    'name': 'Multiple Branch / Unit Operation for Accounting',
    'version': '1.0.1',
    'category': 'Account',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'summary': """ Multiple Branch / Unit Operation for Accounting """,
    'description': """ Multiple Branch / Unit Operation for Accounting """,
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1', 
    "depends": ['acs_branch_base','account'],
    "data": [
        'security/security.xml',
        'views/account_move_view.xml',
        'views/account_payment_view.xml',
        'views/branch_base_view.xml',
        'report/invoice_report_view.xml',
    ],
    'images': [
        'static/description/almightycs_odoo_multi_branch.png',
    ],
    'installable': True,
    'application': False,
    'sequence': 2,
    'price': 20,
    'currency': 'USD',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: