#-*- coding:utf-8 -*-

{
    'name': 'Payroll Localization',
    'category': 'Human Resources',
    'sequence': 38,
    'summary': 'Manage your employee payroll records',
    'description': "",
    'license': 'LGPL-3',
    'depends': [
        'account',
        'hr_contract',
        'base',
        'date_range',
    ],
    'data': [
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'wizard/date_range_generator.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payroll_account_views.xml',
        'data/hr_payroll_data.xml',
        'data/hr_payroll_sequence.xml',
        'views/res_config_settings_views.xml',
        'views/date_range.xml',
        'views/account_fiscal_year.xml',
        'views/account_views.xml',
        'views/res_bank.xml',
        'views/contacts_partner_views.xml',
        'views/res_company.xml',
        'views/hr_employee.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'l10n_hr_payroll_base/static/src/css/custom_style.css',
        ],
    },
}
