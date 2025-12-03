# ============================================================
# FILE: __manifest__.py
# ============================================================
{
    'name': 'Three-Layer Time Off Approval System',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Three-layer approval: Team Manager → HR/Admin Manager → Approved',
    'description': """
        Three-Layer Time Off Approval System
        =====================================
        * Layer 1 (Mandatory): Team Manager approval
        * Layer 2 (Conditional): HR Manager OR Administration Manager approval (either one)
        * Layer 3 (Final): Approved state

        Workflow:
        ---------
        Employee Submits → Team Manager Approves → HR/Admin Approves → Approved

        Features:
        ---------
        * Uses Odoo's default Approve/Refuse buttons
        * Flexible second approval (HR or Admin)
        * Role-based access control
        * Comprehensive tracking
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['hr_holidays'],
    'data': [

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

