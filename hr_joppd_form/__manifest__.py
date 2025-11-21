# -*- coding: utf-8 -*-
{
    'name': 'JOPPD form',

    'summary': """
        JOPPD form""",
    'description': """
        JOPPD form features and reports""",
    
    'author': "Info3 d.o.o.",
    'website': "",
    'category': 'Accounting',
    'license': 'LGPL-3',
    'depends': [
        'l10n_hr_hr' # employee oib is added in l10n_hr_hr module
    ],

    'data': [
        'security/hr_joppd_form_security.xml', # has to be before ir.model.access

        'data/report_paperformat_data.xml',
        'data/hr.report.csv',
        'data/hr.report.line.csv',
        'data/l10n.hr.joppd.sifre.csv',

        'wizard/update_joppd_form_b_lines.xml',

        'reports/report_joppd_form_a.xml',
        'reports/report_joppd_form_b.xml',
        'reports/hr_joppd_form_reports.xml',

        'views/res_company_view.xml',
        'views/hr_joppd_form_views.xml',

        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
