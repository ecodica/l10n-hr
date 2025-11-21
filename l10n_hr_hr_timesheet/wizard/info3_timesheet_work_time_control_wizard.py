from odoo import api, fields, models, _
from datetime import datetime
import workdays
from ..models import timesheet_common as TIMECOM

class info3_timesheet_work_time_control_wizard(models.TransientModel):
    _name = "info3.timesheet.work.time.control.wizard"
    _description = "Work hours control wizard"


    def _set_default_period(self):
        """
        This method set today period
        """
        today_date = datetime.now()
        period_obj = self.env['date.range']
        period_domain = [
            ('date_start', '<=', today_date),
            ('date_end', '>=', today_date),
            ('company_id', '=', self.env.user.company_id.id)
        ]
        period_id = period_obj.search(period_domain)
        return period_id

    
    choice = fields.Selection([('l', 'Less'), ('m', 'More'), ('e', 'Equal'), ('a', 'All')], 'Choice', default='l') 
    less_hours = fields.Boolean('Less hours') 
    more_hours = fields.Boolean('More hours') 
    period_id = fields.Many2one('date.range', 'Period from', default=_set_default_period, ondelete='restrict', required=True) 
    sum_of_hours = fields.Integer('Sum of hours', default=0)
    write_hours = fields.Boolean('Write hours', default=False) 
    employee_lines = fields.One2many('info3.timesheet.work.time.control.wizard.line', 'timesheet_wizard_id', 'Employees') 

    @api.onchange('choice','period_id','sum_of_hours','write_hours')
    def onchange_report(self):
        """
        Calculates working hours in given date span.
        """
        employee_lines = []

        if not self.period_id:
            return {'value': {'employee_lines': employee_lines}}

        period_start = self.period_id.date_start
        period_stop = self.period_id.date_end

        if period_start == period_stop:
            return {'value': {'employee_lines': employee_lines}}

        # Calculate work hours
        workday_diff = workdays.networkdays(period_start, period_stop)
        period_work_hours = workday_diff * 8

        if self.sum_of_hours and self.write_hours:
            period_work_hours = self.sum_of_hours

        # Get active employees into employee list
        emp_obj = self.env['hr.employee']
        emp_ids = emp_obj.search([('active', '=', True)])
        employees_list = []
        for emp in emp_ids:
            employee_tuple = (emp.id, emp.name, emp.department_id.name)
            if employee_tuple not in employees_list:
                employees_list.append(employee_tuple)

        # Get timesheets for selected period
        sheet_obj = self.env['info3.timesheet']
        sheet_ids = sheet_obj.search([('date', '>=', period_start), ('date', '<=', period_stop)])
        sheet_list = []
        for sheet in sheet_ids:
            sheet_list.append(sheet)

        # Merge employees with timesheets
        for emp in employees_list:
            hours = 0
            for sheet in sheet_list:
                if sheet.employee_id.id == emp[0] and sheet.employee_id.active == True:
                    hours += sum([sheet[field] for field in TIMECOM.get_categories()['work_hours']])

            line = {
                'employee_name': u'{0}'.format(emp[1]),
                'department': u'{0}'.format(emp[2]),
                'max_work_hours': period_work_hours,
                'hours': hours
            }
            if self.choice == 'e' and hours == period_work_hours:
                employee_lines.append(line)
            elif self.choice == 'l' and hours < period_work_hours:
                employee_lines.append(line)
            elif self.choice == 'm' and hours > period_work_hours:
                employee_lines.append(line)
            elif self.choice == 'a':
                employee_lines.append(line)
            else:
                continue
        self.employee_lines = [(5, 0, 0)] + [(0, 0, line) for line in employee_lines]
        self.sum_of_hours = period_work_hours


class Info3TimesheetWorkTimeControlWizardLine(models.TransientModel):
    _name = "info3.timesheet.work.time.control.wizard.line"
    _description = "Employee line for work hours control wizard"

    employee_name = fields.Char('Name') 
    department = fields.Char('Department') 
    hours = fields.Float('Hours', default=0) 
    max_work_hours = fields.Float('Max work hours') 
    timesheet_wizard_id = fields.Many2one('info3.timesheet.work.time.control.wizard', 'Timesheet wizard id') 
