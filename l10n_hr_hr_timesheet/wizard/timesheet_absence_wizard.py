from odoo import api, fields, models, _
from datetime import date
import calendar
from collections import defaultdict


class TimesheetAbsenceWizard(models.TransientModel):
    _name = "timesheet.absence.wizard"
    _description = "Employee timesheet absence wizard"

    date_from = fields.Date(required = True)
    date_to = fields.Date(required = True)

    def print_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('l10n_hr_hr_timesheet.info3_timesheet_absence_report').report_action(self, data=data)


    def send_timesheet_absent_employees_notification(self):
        date_from = date(date.today().year, date.today().month, 1)
        last_day = calendar.monthrange(date.today().year, date.today().month)
        date_to = date(date.today().year, date.today().month, last_day[1])
        wizard = self.env['timesheet.absence.wizard'].create({
            'date_from': date_from,
            'date_to': date_to,
            })
        
        group = self.env.ref('l10n_hr_hr_timesheet.group_hr_hr_timesheet_receive_notification')
        receivers = self.env['res.users'].search([('groups_id', 'in', group.id)])

        self.send_emails(receivers, wizard)
        return True

    def send_emails(self, receivers, wizard):
        template = self.get_timesheet_absent_employees_mail_template()

        ReportsCommon = self.env['hr.hr.payroll.reports.common']
        records_count = self.env['info3.timesheet'].search_count([('date', '>=', wizard.date_from),('date', '<=', wizard.date_to), ('absence_fault', '>', 0)])

        if len(receivers)>0:
            receivers_dict = defaultdict(list)
            for receiver in receivers:
                receivers_dict[receiver.lang].append(receiver)

            for language in receivers_dict:
                date_format = ReportsCommon._date_format(language)
                c = {
                    'recipients': ', '.join([user.email for user in receivers_dict[language]]),
                    'date_from': wizard.date_from.strftime(date_format),
                    'date_to': wizard.date_to.strftime(date_format),
                    'records_count': records_count,
                    'wizard': wizard,
                    'from_cron': True,
                    'lang': language,
                    'active_ids': wizard.ids,
                    'active_model': wizard._name
                }
                template.with_context(c).send_mail(self.env.user.company_id.id)
        return True
    
    def get_timesheet_absent_employees_mail_template(self):
        return self.env.ref('l10n_hr_hr_timesheet.mail_template_employee_absence')

    def get_date_range(self):
        last_day = calendar.monthrange(date.today().year, date.today().month)

        self.date_from = date(date.today().year, date.today().month, 1)
        self.date_to = date(date.today().year, date.today().month, last_day)

        return True