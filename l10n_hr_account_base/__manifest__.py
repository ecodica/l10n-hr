{
    "name": "Croatia - Accounting base",
    "summary": "Croatia accounting localisation",
    "category": "Accounting/Localizations/Croatia",
    "images": [],
    "version": "18.0.4.0.0",
    "application": False,
    "author": "Ecodica d.o.o., Standard Croatian Localization",
    "website": "https://github.com/OCA/l10n-croatia",
    "license": "LGPL-3",
    "depends": [
        "account",
        "base_vat",
        "base_iban",
        "l10n_hr_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_view.xml",
        "views/fiscal_data_views.xml",
        "views/account_move_view.xml",
        "views/account_journal_view.xml",
        "views/res_partner_views.xml",
        "views/menuitems.xml",
        "report/report_invoice.xml",
    ],
    "assets":{
        'web.assets_backend': [
            'l10n_hr_account_base/static/src/tax_totals/tax_totals.xml',
        ]
    },
    "auto_install": False,
    "installable": True,
}
