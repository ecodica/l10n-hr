# -*- coding: utf-8 -*-
{
    'name': 'Croatian payroll',

    'summary': """
        Payroll""",
    'description': """
        Payroll localization for Croatia""",

    'author': "Info3 d.o.o.",
    'website': "",
    'category': 'Human Resources',
    'version':'18.0.1.0.0',
    'license': 'LGPL-3',
    'depends': [
        'l10n_hr_hr',
        'l10n_hr_payroll_base',
        'hr_joppd_form',
        'mail',
        'report_xlsx',
        #'l10n_hr_pain_credit_transfer', #zbog *.xsd pain datoteke za SEPA
        'l10n_hr_hr_timesheet',
        #dodati account_payment_order?
    ],

    'data': [
        'data/report_paperformat_data.xml', # has to be before the reports

        'security/hr_hr_payroll_security.xml', # has to be before ir.model.access
        'security/hr_hr_payroll_security_override_noupdate.xml',
        'reports/report_additional_income.xml',
        'reports/report_contributions_recap.xml',
        'reports/report_employee_average_salary.xml',
        'reports/report_employee_recap.xml',
        'reports/report_fees_earnings.xml',
        'reports/report_hr_payslip_run_recap.xml',
        'reports/report_hr_payslip_run_suspensions.xml',
        'reports/report_ip_form.xml',
        'reports/report_ip1_form.xml',
        'reports/report_payslip_confirmation.xml',
        'reports/report_tax_city.xml',
        'reports/report_work_statistics.xml',
        'reports/report_io1.xml',
        'reports/report_hr_payslip_forced_payment_request.xml',
        'reports/report_no1.xml',

        'reports/hr_hr_payroll_reports.xml',         # this is where reports are defined, has to be before hr_payslip_views and after reports
        
        'wizard/payslip_run_reports_wizard.xml', # contains Reports menuitem so has to be before all children
        'wizard/add_inputs_wizard.xml', # has to be before hr_payslip_views
        'wizard/info3_sepa_form.xml',
        'wizard/sick_leave_average_wage_wizard.xml', # has to be before hr_contract_view
        'wizard/unused_annual_leave_average_gross_wage_wizard.xml',
        'wizard/hr_payroll_payslips_by_employee.xml',
        'wizard/assign_annual_leave_wizard.xml',
        'wizard/info3_payslip_confirmation.xml',
        'wizard/additional_income_report_wizard.xml',
        'wizard/contributions_recap_report_wizard.xml',
        'wizard/ip_report_wizard.xml',
        'wizard/work_statistics.xml',
        'wizard/netto_to_brutto.xml',
        'wizard/duplicate_contract.xml',
        'wizard/nonpaid_payslip_wizard.xml',
        'wizard/payslip_forced_payment_request_wizard.xml',
        'wizard/annual_calculation_wizard.xml',
        'wizard/contribution_base_distribution.xml',

        'data/hr.salary.rule.category.csv',
        'data/hr.salary.rule.csv', # contains category refs so needs to be after category import (same thing for sifre)
        'data/hr.payroll.structure.csv', # contains rule refs so needs to be after rule import, also l10n.hr.joppd.sifre refs
        'data/res_city_data.xml',
        'data/tax.deduction.csv',
        'data/info3.work.exp.benefit.csv',
        'data/mail_template_data.xml',
        'data/payroll_data.xml',
        'data/work_experience_fee_limit.xml',
        'data/ip1_form_report_config.xml', # has to be after rules
        'data/tax_deduction_data.xml',
        'data/hr_payroll_config_data.xml',
        'data/res_config_settings_data.xml',
        'data/hr_salary_rule.xml',
        
        'views/hr_employee_annual_leave_views.xml',
        'views/hr_salary_suspension_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_city_view.xml',
        'views/hr_report_views.xml',
        'views/info3_sepa_views.xml',
        'views/hr_payroll_disability_fee_payment_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_salary_parameters_views.xml',
        'views/info3_work_exp_benefit_views.xml',
        'views/tax_deduction_views.xml',
        'views/hr_joppd_form_views.xml',
        'views/hr_payroll_accounting_scheme_type.xml',
        'views/hr_payroll_accounting_scheme.xml',
        'views/work_experience_fee_limit_views.xml',
        'views/ip1_form_report_config_views.xml',
        'views/hr_payroll_config.xml',
        'views/hr_payroll_menus.xml', # contains references to actions so needs to be loaded after all views
        'views/hr_menus.xml', # contains references to actions so needs to be loaded after all views
                
        'security/ir.model.access.csv',
    ],
    'demo': [
#        'demo/hr_payroll_demo.xml'
    ],
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'l10n_hr_hr_payroll/static/src/css/custom_style.css',
        ],
    },

}

