{
    'name': 'Zencore Groups',
    'version': '19.0.1.0.0',
    'summary': 'Universal Security Groups Registry for Zencore Modules',
    'description': """
        Zencore Groups — Universal Security Registry
        =============================================
        Centralised group/privilege definitions for all Zencore custom modules.

        Roles provided:
        ─────────────────────────────────────────────────────────────────
        Role            XML ID                              Scope
        ─────────────────────────────────────────────────────────────────
        Salesperson     group_zencore_clm_salesperson       Sales
        Sales Manager   group_zencore_clm_sales_manager     Sales
        CCM             group_zencore_clm_ccm               Credit Control
        Warehouse       group_zencore_clm_warehouse         Inventory
        TDO             group_zencore_clm_tdo               Delivery / Invoicing
        Finance         group_zencore_clm_finance           Payments / Approval
        ─────────────────────────────────────────────────────────────────

        Other modules add this to their `depends` list and reference groups
        with the 'zencore_groups' module prefix:

            self.env.user.has_group('zencore_groups.group_zencore_clm_finance')
            groups="zencore_groups.group_zencore_clm_ccm"
    """,
    'author': 'Madhusudan Ray',
    'website': 'https://zencoreltd.com',
    'category': 'msa',       # Hidden: infrastructure module, not end-user app
    'depends': ['base'],        # Only base — no business module dependencies
    'data': [
        'security/group_security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}