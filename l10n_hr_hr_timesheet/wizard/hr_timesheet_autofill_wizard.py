from odoo import api, fields, models, _
from datetime import datetime, timedelta
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

# leave types which override regular hours (for other leave types we want regular hours on timesheet)
TIMESHEET_LEAVE_TYPES = [
    'annual_leave',
    'sick_leave',
    'sick_leave_fund',
    'paid_leave',
    'unpaid_leave',
    'maternity_leave',
    'parental_leave'
]


class HrTimesheetAutofillWizard(models.TransientModel):
    _name = "hr.timesheet.autofill.wizard"
    _description = "Timesheet autofill"

    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get('hr.timesheet.autofill.wizard'),)  
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    employee_line_ids = fields.One2many('hr.timesheet.autofill.wizard.line', 'wizard_id', 'Employees')
    employee_filter_ids = fields.Many2many('hr.employee', help='Employee filter')

    workday_start_time = fields.Float("Workday start time", default=0.00)
    workday_end_time = fields.Float("Workday end time", default=0.00)
    show_only_leaves = fields.Boolean(string="Show only leaves", default=False)

    def get_employees_data(self):
        #from hr_hr_payroll_extra override
        self.employee_line_ids = False
        data = self._prepare_employees_data()
        self.employee_line_ids = data

        model, res_id = self.env['ir.model.data']._xmlid_lookup('l10n_hr_hr_timesheet.action_hr_timesheet_autofill_wizard')
        action = self.env[model].browse(res_id)

        if action:
            action_data = action.read()[0]
            action_data['res_id'] = self.id 
            return action_data

    def _prepare_employees_data(self):
        #dict with list of all info3.timesheet records in defined period
        date_from = self.date_from
        date_to = self.date_to
        existing_timesheet_records = {
            (t.employee_id.id,t.date): t.id for t in self.env['info3.timesheet'].search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to)])}
        employee_data = {}

        emps = self.employee_filter_ids or self.env['hr.employee']._get_employees_by_tag(include_inactive=False)

        if not self.show_only_leaves:
            self._add_regular_hours(employee_data, date_from, date_to, existing_timesheet_records, emps)

        self._add_leaves(employee_data, date_from, date_to, existing_timesheet_records, emps)

        formatted_data = []
        for emp_key, emp_data in employee_data.items():
            formatted_data.append((0, 0, emp_data))

        return formatted_data

    def _add_regular_hours(self, employee_data, date_from, date_to, existing_timesheet_records, emps):
        holidays = self.env['hr.holiday'].search([('date', '>=', date_from), ('date', '<=', date_to)])
        holiday_dates = [h.date for h in holidays]

        day_count = (date_to - date_from).days + 1
        for date in (date_from + timedelta(n) for n in range(day_count)):
            for e in emps:
                is_weekend = date.weekday() > 4
                not_hired_yet = e.hire_date and (date < e.hire_date)
                contract_terminated = e.contract_id.termination_date and (date > e.contract_id.termination_date)

                if is_weekend or not_hired_yet or contract_terminated:
                    continue

                emp_key = (e.id,date)
                if not employee_data.get(emp_key,False):
                    start_time = self.workday_start_time
                    end_time = self.workday_end_time
                    total = end_time - start_time
                    holiday = 0.0
                    if date in holiday_dates:
                        start_time = 0.0
                        end_time = 0.0
                        total = 0.0
                        holiday = 8.0
                    employee_data[emp_key] = {
                        'employee_id': emp_key[0],
                        'department_id': e.department_id.id,
                        'date': emp_key[1],
                        'start_time': start_time,
                        'end_time': end_time,
                        'total': total,
                        'annual_leave_hours': 0.0,
                        'sick_leave': 0.0,
                        'sick_leave_fund': 0.0,
                        'paid_leave': 0.0,
                        'unpaid_leave': 0.0,
                        'maternity_leave': 0.0,
                        'parental_leave': 0.0,
                        'holiday': holiday,
                        'timesheet_id': existing_timesheet_records.get(emp_key,False),
                    }
    def _search_hr_leaves(self,date_from,date_to,emps):
        return ['|','&', ('request_date_from','>=', date_from), ('request_date_from','<=', date_to),
            '&', ('request_date_to', '>=', date_from), ('request_date_to','<=', date_to),
            ('state', 'not in', ['cancel','refuse']),
            ('holiday_status_id.i3_leave_type', 'in', TIMESHEET_LEAVE_TYPES),
            ('employee_id', 'in', emps.ids)]

    def _add_leaves(self, employee_data, date_from, date_to, existing_timesheet_records, emps):
        for l in self.env['hr.leave'].search(self._search_hr_leaves(date_from,date_to,emps)):
            if not l.request_date_from or not l.request_date_to:
                continue
            req_date_from = max(l.request_date_from, date_from)
            req_date_to = min(l.request_date_to, date_to)
            day_count = (req_date_to - req_date_from).days + 1
            employee_id = l.employee_id.id
            day_hours = {}
            self.set_employee_day_hours(employee_id, day_hours)

            for date in (req_date_from + timedelta(n) for n in range(day_count)):
                if date.weekday() > 4:
                    continue
                emp_key = (employee_id,date)
                # only case where emp_key is not present should be when employee is archived and has a leave in the period
                # we don't want the autofill feature to crash for this case
                # adding leaves seems like a better solution than raising an error because user can edit data afterwards
                # (even though they are not notified, they usually control the data using reports before proceeding with the payroll calculation process)
                # if we raise an error then they first have to sort out data to get any kind of preview
                if emp_key not in employee_data:
                    employee_data.update({
                        emp_key: {
                            'employee_id': emp_key[0],
                            'department_id': l.employee_id.department_id.id,
                            'date': emp_key[1],
                            'timesheet_id': existing_timesheet_records.get(emp_key,False),
                        }
                    })
                employee_data[emp_key]['start_time'] = 0.0
                employee_data[emp_key]['end_time'] = 0.0
                employee_data[emp_key]['total'] = 0.0
                
                if l.holiday_status_id.i3_leave_type == 'annual_leave':
                    employee_data[emp_key]['annual_leave_hours'] = day_hours[employee_id]
                elif l.holiday_status_id.i3_leave_type == 'sick_leave':
                    employee_data[emp_key]['sick_leave'] = day_hours[employee_id]
                elif l.holiday_status_id.i3_leave_type == 'sick_leave_fund':
                    employee_data[emp_key]['sick_leave_fund'] = day_hours[employee_id]
                elif l.holiday_status_id.i3_leave_type == 'paid_leave':
                    employee_data[emp_key]['paid_leave'] = day_hours[employee_id]
                elif l.holiday_status_id.i3_leave_type == 'unpaid_leave':
                    employee_data[emp_key]['unpaid_leave'] = day_hours[employee_id]
                elif l.holiday_status_id.i3_leave_type == 'maternity_leave':
                    employee_data[emp_key]['maternity_leave'] = day_hours[employee_id]
                elif l.holiday_status_id.i3_leave_type == 'parental_leave':
                    employee_data[emp_key]['parental_leave'] = day_hours[employee_id]

    def update_employees(self):
        timesheet_obj = self.env['info3.timesheet']
        
        #each employee in self
        for line in self.employee_line_ids:
            values = {
                'employee_id': line.employee_id.id,
                'department_id': line.department_id.id,
                'date': line.date,
                'start_time': line.start_time,
                'end_time': line.end_time,
                'department_id': line.department_id.id,
                'total': line.total,
                'annual_leave_hours': line.annual_leave_hours,
                'sick_leave': line.sick_leave,
                'paid_leave': line.paid_leave,
                'sick_leave_fund': line.sick_leave_fund,
                'unpaid_leave': line.unpaid_leave,
                'maternity_leave': line.maternity_leave,
                'parental_leave': line.parental_leave,
                'holiday': line.holiday,
            }

            if line.timesheet_id:
                line.timesheet_id.write(values)
            else:
                timesheet_obj.create(values)

        return {'type': 'ir.actions.act_window_close'}

    def set_employee_day_hours(self, employee_id, day_hours):
        hr_salary_parameter = self.env['hr.salary.parameters'].search([
            ('employee_id', '=', employee_id),
            ('date_from', '<=', self.date_to)
        ], order="date_from desc")
        if hr_salary_parameter:
            day_hours[employee_id] = hr_salary_parameter[0].day_hours
        else:
            day_hours[employee_id] = 8.0



class HrTimesheetAutofillWizardLine(models.TransientModel):
    _name = "hr.timesheet.autofill.wizard.line"
    _description = 'HR timesheet autofill wizard line'


    wizard_id = fields.Many2one('hr.timesheet.autofill.wizard', 'Wizard')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    employee_view_id = fields.Many2one('hr.employee', 'Employee View')
    timesheet_id = fields.Many2one('info3.timesheet', 'Timesheet record')
    date = fields.Date('Date')
    date_view = fields.Date('Date View')
    start_time = fields.Float('Start of work')
    end_time = fields.Float('End of work')
    total = fields.Float('Total hours')
    annual_leave_hours = fields.Float('Annual leave hours', help="Hours of annual leave")
    sick_leave = fields.Float('Sick leave hours', help="Hours of sick leave paid by company")
    paid_leave = fields.Float('Paid leave hours', help="Hours of paid leave")
    holiday = fields.Float('Holiday', help="Hours on a holiday")
    replace_existing = fields.Boolean('Replace existing', default=False)
    department_id = fields.Many2one('hr.department', 'Department')
    unpaid_leave = fields.Float('Unpaid leave hours')
    maternity_leave = fields.Float('Maternity leave hours')
    parental_leave = fields.Float('Parental leave hours')
    sick_leave_fund = fields.Float('Sick leave fund hours', help="Hours of sick leave paid by health insurance fund")

    @api.onchange('start_time', 'end_time')
    def _compute_total(self):
        self.total = self.end_time - self.start_time

