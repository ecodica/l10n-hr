# -*- coding: utf-8 -*-
# Copyright 2023 Ecodica
{
    "name": """Cash Register""",
    "summary": """Cash Register""",
    "category": "Croatia",
    "version": "17.0.1.0.0",
    "application": False,
    'author': "Ecodica",
    "license": 'LGPL-3',
    'website': "https://www.ecodica.eu",
    "support": "support@ecodica.eu",
    "depends": [
        "account_accountant",
    ],
    "data": [
        "report/cash_register_report.xml",
        "views/account_bank_statement_line_views.xml",
    ],
    "auto_install": False,
    "installable": True,
}
