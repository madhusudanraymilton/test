{
    "name": "Todo Practice",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "summary": "Job Tracking and Report Practice Module",
    "description": """
Todo Practice
==================================
This module is used for practicing:
- Custom models
- Modern views
- PDF reports using QWeb
- Job Tracking workflow
""",
    "author": "Madhusudan Ray",
    "website": "https://www.madhusudanray.com",
    "license": "LGPL-3",

    "depends": [
        "base",
        "mail",       # needed for chatter
        "web",        # required for QWeb PDF reports
    ],

    "data": [
        # Security
        "security/ir.model.access.csv",

        # Views
        "views/job_tracking_views.xml",

        # Reports (order matters)
        "report/reports.xml",        # ir.actions.report
        "report/job_report.xml",     # QWeb template
    ],

    "installable": True,
    "application": True,
    "auto_install": False,
}
