# -*- coding: utf-8 -*-
{
    'name': "l10n_hr_hr",

    'summary': """
        HR module Croatian localization
    """,

    'description': """
         HR module Croatian localization
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'depends': [
        'web',
        'hr',
        'hr_contract',
        'website_hr_recruitment',
        'l10n_hr_payroll_base',
        'base_address_extended',
        'hr_holidays',
        'hr_skills',
    ],

    'data': [
        'security/hr_security.xml',
        'security/hr_security_override_noupdate.xml',
        'security/ir.model.access.csv',
        'views/hr_job_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_category_type_views.xml',
        'views/hr_experience_type_views.xml',
        'views/hr_contract_document_type_views.xml',
        'views/hr_contract_area_type_views.xml',
        'views/hr_contract_subarea_type_views.xml',
        'views/hr_contract_interruption_reason_type_views.xml',
        'views/hr_disability_type_views.xml',
        'views/hr_status_views.xml',
        'views/res_partner_views.xml',
        'views/address_type_views.xml',
        'views/hr_education_type_views.xml',
        'views/hr_inactivity_type_views.xml',
        'views/hr_transportation_type_views.xml',
        'views/hr_transportation_carrier_views.xml',
        'views/hr_driving_licence_categories_views.xml',
        'views/hr_education_institution_views.xml',
        'views/hr_contract_views.xml',
        'views/res_company_view.xml',
        'views/hr_department.xml',
        'views/hr_leave_views.xml',
        'views/hr_work_permit_views.xml',
        'views/hr_employee_degree_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_medical_exam_views.xml',
        'views/hr_payroll_structure_type_views.xml',

        'report/report.xml',
        'report/report_hr_employee_experience.xml',
        'report/report_hr_employee.xml',
        'report/report_hr_main_register.xml',
        'report/report_hr_contracts.xml',
        'report/report_hr_employee_contracts.xml',

        'data/hr_contract_data.xml',
        'data/hr_address_types.xml',
        'data/employee_tags.xml',

        'wizard/hr_employee_registration_wizard.xml',
    ],

    'assets': {

    'web.assets_backend': [
        'l10n_hr_hr/static/src/css/hr_hr.css',
    ],
    }
}
