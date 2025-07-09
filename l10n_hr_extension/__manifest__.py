# -*- coding: utf-8 -*-

{
    'name': 'Croatia - Accounting (Euro) - Extension',
    'summary': 'Croatian Chart of Accounts updated (RRIF ver. 2021) - updated version',
    'category': 'Accounting/Localizations/Account Charts',
    'icon': '/account/static/description/l10n.png',
    'countries': ['hr'],
    'version': '1.0',
    'application': False,
    'description': """
Croatia - Invoicing
===================
    """,

    'author': 'Notus IT d.o.o.',
    'support': 'odoo@notus.hr',
    'website': 'https://www.notus.hr',
    'license': 'OPL-1',

    'depends': [
        # Odoo modules
        'l10n_hr',
        # Notus modules
        'account_tax_clause',
    ],
    'external_dependencies': {
        'python': [],
        'bin': []
    },

    'data': [
        'data/account_account_data.xml',
        'data/account_account_tag_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_data.xml',
        'data/account_fiscal_position_data.xml',
    ],
    'qweb': [],
    'demo': [],

    'installable': True,
    'auto_install': True,

    'post_load': None,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': None,
}
