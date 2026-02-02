# -*- coding: utf-8 -*-

{
    "name": "OBE Core – Academic & Outcome Framework",
    "version": "18.0.1.0.0",
    "summary": "Core academic structure and outcome definitions for Outcome-Based Education",
    "description": """
OBE Core Module (Odoo 18)

This module provides the foundational academic and Outcome-Based Education (OBE)
data structures required for accreditation-compliant education systems.

Included:
• Institutional Vision & Mission
• Academic Programs & Courses
• Program Educational Objectives (PEO)
• Program Learning Outcomes (PLO)
• Course Learning Outcomes (CLO)
• CLO–PLO & PLO–PEO mappings
• Outcome versioning readiness
• Role-based access control

Excluded:
• Assessment
• Attainment calculation
• Dashboards & reports

This module is designed to be a stable dependency for higher-level
OBE analytics and assessment modules.
""",

    "author": "Your Organization / University",
    "website": "https://www.yourorganization.com",
    "category": "Education",
    "license": "LGPL-3",

    # Odoo 18 Dependencies
    "depends": [
        "base",
        "mail",
        "web",
    ],

    # Data files (order matters)
    "data": [
        # Security
        # "security/obe_security.xml",
        # "security/obe_record_rules.xml",
        "security/ir.model.access.csv",

       
        # Institutional setup
        "views/institution_views.xml",
        # "views/program_views.xml",

        # Outcomes
        # "views/peo_views.xml",
        # "views/plo_views.xml",
        # "views/clo_views.xml",

        # Courses
        # "views/course_views.xml",
        # "views/course_offering_views.xml",

        # Mapping
        # "views/mapping_views.xml",

         # Menus
        "views/menu_views.xml",

    ],

    "demo": [
        # "data/demo_data.xml",
    ],

    "application": True,
    "installable": True,
    "auto_install": False,

}
