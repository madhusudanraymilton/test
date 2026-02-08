# -*- coding: utf-8 -*-
{
    'name': 'OBE Core - Outcome-Based Education Management',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Comprehensive OBE Management System for Academic Institutions',
    'description': """
Outcome-Based Education (OBE) Core Module
==========================================

This module provides comprehensive tools for managing Outcome-Based Education (OBE)
in universities and engineering faculties, supporting BAETE, ABET, and NBA accreditation.

Key Features:
-------------
* Institution Vision & Mission Management
* Program Educational Objectives (PEO) with approval workflow
* Program Learning Outcomes (PLO) with accreditation mapping
* Course Learning Outcomes (CLO) with Bloom's taxonomy
* Multi-level mapping (CLO-PLO-PEO) with strength indicators
* Course and offering management
* Security with role-based access control
* Complete audit trail and versioning
* Designed for accreditation compliance

Supported Standards:
-------------------
* BAETE (Bangladesh Accreditation Council)
* ABET (Accreditation Board for Engineering and Technology)
* NBA (National Board of Accreditation - India)
* Washington Accord Graduate Attributes

Target Users:
-------------
* System Administrators
* Accreditation Coordinators
* Department Heads
* Program Coordinators
* Faculty Members
* QA Officers
    """,
    'author': 'Your Organization',
    'website': 'https://www.yourorganization.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
        'hr',
        'website'
    ],
    'data': [
        'security/obe_security.xml',
        'security/ir.model.access.csv',

        'views/institution_views.xml',
        'views/academic_program_views.xml',
        'views/course_views.xml',
        'views/clo_views.xml',
        'views/plo_views.xml',
        'views/peo_views.xml',
        'views/course_offering_views.xml',
        'views/clo_plo_mapping_views.xml',
        'views/peo_plo_mapping_views.xml',
        'views/obe_assessment views.xml',
        #'views/clo_plo_matrix_qweb.xml',
        #'views/clo_plo_matrix_web_views.xml',
        #'views/clo_plo_matrix_wizard_enhanced.xml',
    ],
    'demo': [
        
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    # 'sequence': 10,
    # 'post_init_hook': 'post_init_hook',
}