# -*- coding: utf-8 -*-

{
    'name': 'Accounting Tax Clause',
    'summary': 'This module adds support for tax clauses.',
    'category': 'Accounting/Accounting',
    'images': [],
    'version': '1.0',
    'application': False,
    'description': """
Accounting Tax Clause
=====================

This module adds support for tax clauses on invoice.
""",
    'author': 'Notus IT d.o.o.',
    'support': 'odoo@notus.hr',
    'website': 'https://www.notus.hr',
    'license': 'OPL-1',

    'depends': [
        # Odoo modules
        'account',
        # OCA addons
        # Notus modules
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },

    'data': [
        'views/account_tax_views.xml',
        'views/account_move_views.xml',
        'report/report_invoice_templates.xml',
    ],
    'qweb': [],
    'demo': [],

    'installable': True,
    'auto_install': False,

    'post_load': None,
    'pre_init_hook': None,
    'post_init_hook': None,
}
