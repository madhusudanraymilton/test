{
    "name": "My REST API",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "summary": "Custom REST API for external integration",
    "description": """
This module provides REST API endpoints using JSON-RPC/HTTP
to connect external applications with Odoo 19.
""",
    "author": "Madhusudan Ray",
    "website": "https://yourwebsite.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "hr"
    ],
    "data": [
        # security
        #"security/ir.model.access.csv",

        # if you use custom groups
        # "security/security.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
