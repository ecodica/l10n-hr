# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import calendar
import time
from ..models import timesheet_common as TIMECOM


class Info3TimesheetReportSum(models.AbstractModel):
    _name = 'report.l10n_hr_hr_timesheet.report_info3_timesheet_sum'
    _description = 'Timesheet report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_obj = self.env['report.l10n_hr_hr_timesheet.report_info3_timesheet']
        if not data['month'] or not data['year']:
            raise ValidationError(_("Mjesec i godina moraju biti odabrani!"))
        emp_obj = self.env['hr.employee']
        #variable to check report type
        sum_report = True
        report_lines = report_obj.get_report_lines(data, sum_report)
        # a single emp_id is needed for the report to print
        emps = emp_obj.search([],limit=1)
        return {
            'doc_ids': emps.ids,
            'doc_model': 'hr.employee',
            'docs': emps,
            'report_lines': report_lines,
        }
