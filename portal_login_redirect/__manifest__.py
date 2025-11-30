{
    'name': 'Portal Login Redirect',
    'version': '1.0',
    'summary': 'Redirect portal user to /my after login',
    'description': """
Automatically redirect portal users to /my after successful login.
""",
    'author': 'Madhusudan Ray',
    'category': 'Website',
    'depends': [
        'web',
        'base',
        'website',
        'portal',
    ],
    'data': [
        # we don't need XML for redirect, but keeping folder for future
        'views/dashboard_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
