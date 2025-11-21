# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class WorkStatisticsWizard(models.TransientModel):
    _name = 'work.statistics.wizard'
    _description = 'Payroll work statistics wizard'

    date = fields.Date('Date', required=True)

    def print_work_statistics(self):
        data = {}
        data['date'] = self.date

        report_id = 'l10n_hr_hr_payroll.hr_report_work_statistics'
        report_action = self.env.ref(report_id).report_action(self, data=data)
        return report_action