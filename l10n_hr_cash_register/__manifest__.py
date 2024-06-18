# -*- coding: utf-8 -*-
# Copyright 2023 Ecodica
{
    "name": """Cash Register""",
    "summary": """Cash Register""",
    "category": "Croatia",
    "images": [],
    "version": "16.0.0.0.1",
    "application": False,
    'author': "Ecodica",
    "license": 'LGPL-3',
    'website': "https://www.ecodica.eu",
    "support": "support@ecodica.eu",

    "depends": [
        "account_accountant",
    ],
    "external_dependencies": {
        "python": [],
        "bin": []
    },
    "data": [
        'security/ir.model.access.csv',
        "data/report_paperformat_data.xml",
        "report/cash_register_report.xml",
        "report/cash_register_period_report.xml",
        "wizard/cash_register_period_report_wizard_views.xml",
        "views/account_bank_statement_line_views.xml",
    ],
    "qweb": [],
    "demo": [],

    "auto_install": False,
    "installable": True,
}
