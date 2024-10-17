{
    'name': 'Croatia - Invoice Tips Fiskal',
    'summary': 'Croatia Invoice Tips Fiskalization',
    'category': 'Accounting/Localizations/Croatia',
    'version': '17.0.1.0.0',
    'application': False,
    'author': 'info3',
    'license' : 'OPL-1',
    'website': 'https://info3.hr/hr/',
    'depends': [
        'l10n_hr_account_fiskal',
        'l10n_hr_account_invoice_tips',
    ],
    'data': [
        'views/account_move_view.xml',
        'views/res_company.xml',
        'wizards/invoice_tips_report_wizard.xml',
        'report/invoice_report_tips.xml',
    ],

    'auto_install': True,
    'installable': True,
}
