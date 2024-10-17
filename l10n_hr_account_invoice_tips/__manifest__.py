{
    'name': 'Croatia - Invoice Tips',
    'summary': 'Croatia Invoice Tips',
    'category': 'Accounting/Localizations/Croatia',
    'version': '17.0.1.0.0',
    'application': False,
    'author': 'info3',
    'license' : 'OPL-1',
    'website': 'https://info3.hr/hr/',
    'depends': [
        'l10n_hr_account_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_move_view.xml',
        'wizards/invoice_tips_report_wizard.xml',
        'report/invoice_report_tips.xml',
    ],
    'auto_install': False,
    'installable': True,
}
