# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import calendar
import time
from ..models import timesheet_common as TIMECOM


class Info3TimesheetReportAbsence(models.AbstractModel):
    _name = 'report.report_info3_timesheet_absence'
    _description = 'Timesheet employee absence report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        from_cron = self.env.context.get('from_cron', False)
            
        doc_ids = self.env.context['active_ids']
        doc_model = self.env.context['active_model']
        docs = self.env[doc_model].browse(doc_ids)
        lang = self.env.context.get('lang')
        date_from = docs.date_from
        date_to = docs.date_to

        ReportsCommon = self.env['hr.hr.payroll.reports.common']
        if from_cron:
            date_format = ReportsCommon._date_format(lang)
            time_format = ReportsCommon._time_format(lang)
        else:
            date_format = ReportsCommon._date_format()
            time_format = ReportsCommon._time_format()

        unjustified_absences = self.get_unjustified_absences(date_from, date_to, date_format, time_format)
        report_data = {
            'company': self.env.user.company_id,
            'heading': _('Unjustified employee absence'),
            'date_range': self.get_data_range(date_from, date_to, date_format),
            'header': self.get_header(),
            'unjustified_absences': unjustified_absences,
            'number_of_records': self.get_number_of_records(len(unjustified_absences)),
        }

        return {
            'doc_ids': doc_ids,
            'doc_model': doc_model,
            'docs': docs,
            'data': report_data,
            'lang':lang,
        }

    def get_header(self):
        header = {
            'counter': _('No.'),
            'name': _('Name'),
            'code': _('Code'),
            'department': _('Department'),
            'absence_date': _('Absence date'),
            'entry_date': _('Date of entry'),
        }
        return header

    def get_number_of_records(self, nb_of_records):
        number_of_records = {
            'description': _('Number of records:'),
            'count': nb_of_records
        }
        return number_of_records

    def get_data_range(self, date_from, date_to, date_format):
        date_range = {
            'description': _('Date range:'),
            'date_from': date_from.strftime(date_format),
            'date_to': date_to.strftime(date_format)
        }
        return date_range

    def get_unjustified_absences(self, date_from, date_to, date_format, time_format):
        unjustified_absences = []
        timesheets = self.env['info3.timesheet'].search([('date', '>=', date_from),('date', '<=', date_to), ('absence_fault', '>', 0)])
        timesheets = sorted(timesheets, key=lambda x: (x['employee_id']))

        counter = 1
        for timesheet in timesheets:
            absence = {
                'counter': counter,
                'name': timesheet.employee_id.name,
                'code': timesheet.employee_id.code,
                'department': timesheet.employee_id.department_id.name,
                'absence_date': timesheet.date.strftime(date_format),
                'entry_date': timesheet.write_date.strftime('{0} {1}'.format(date_format, time_format))
            }
            unjustified_absences.append(absence)
            counter += 1

        return unjustified_absences