{
    'name': 'HR timesheet',
    'version': '18.0.1.0.0',
    'author': 'Info3 d.o.o.',
    'company': 'Info3 d.o.o.',
    'license': 'LGPL-3',
    'summary': """Timesheet implementation""",
    "external_dependencies": {"python": ["workdays","PyICU"]},
    'depends': [
        'l10n_hr_hr',
        'hr_holidays',
    ],
    'data': [
        'security/hr_hr_timesheet_security.xml',

        'data/report_paperformat_data.xml',
        'data/ir_cron_data.xml',

        'reports/report_info3_timesheet.xml',
        'reports/report_info3_timesheet_sum.xml',
        'reports/timesheet_reports.xml',
        'reports/report_info3_timesheet_absence.xml',

        'views/hr_holiday_views.xml',
        'views/info3_timesheet.xml',

        'wizard/timesheet_report_wizard.xml',
        'wizard/info3_timesheet_wizard.xml',
        'wizard/info3_timesheet_work_time_control_wizard.xml',
        'wizard/hr_timesheet_autofill_wizard.xml',
        'wizard/timesheet_absence_wizard.xml',

        'security/ir.model.access.csv',
    ],
    'assets':{
        'web.assets_backend':[
            'l10n_hr_hr_timesheet/static/src/**/*',
        ],
    },
    'demo': [
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
}
