from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_monday = _('Ponedjeljak')
_tuesday = _('Utorak')
_wednesday = _('Srijeda')
_thursday = _('Četvrtak')
_friday = _('Petak')
_saturday = _('Subota')
_sunday = _('Nedjelja')

class Info3TimesheetWizard(models.TransientModel):
    _name = "info3.timesheet.wizard"
    _description = "Add multiple employees"

    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env.company)
    date = fields.Date('Date', required=True)
    date_day = fields.Char('Date day', size=12)
    date_to = fields.Date('Date to', required=True, help="Date to which selected employees with given values will be added (max 7 days)")
    date_to_day = fields.Char('Date to day', size=12)
    analytic_account_id = fields.Many2one('account.analytic.account', "Analytic account")

    start_time = fields.Float('Start of work', help="Hours when work was started")
    end_time = fields.Float('End of work', help="Hours when work was completed")
    annual_leave_hours = fields.Float('Annual leave hours', help="Time and hours of annual leave.")
    total = fields.Float('Total hours', help="Total time of work")
    night_work = fields.Float('Night work hours', help="Hours of work at night")
    overtime = fields.Float('Overtime work hours', help="Overtime hours")
    holiday = fields.Float('Holiday', help="Holiday")
    sick_leave = fields.Float('Sick leave hours', help="Hours of sick leave")
    maternity_leave = fields.Float('Maternity leave hours', help="Hours of maternity leave")
    paternity_leave = fields.Float('Paternity leave hours', help="Hours of paternity leave")
    parental_leave = fields.Float('Parental leave hours', help="Hours of parental leave")
    fieldwork = fields.Float('Domestic field work', help="Hours of domestic field work")
    fieldwork_abroad = fields.Float('Field work abroad', help="Hours of field work abroad")
    non_working_holiday = fields.Float('Non-working holiday hours', help="Hours of work on non-working holiday")
    non_working_sunday = fields.Float('Non-working sunday hours', help="Hours of work on non-working sunday")
    sick_leave_fund = fields.Float('Sick leave fund hours')
    paid_leave = fields.Float('Paid leave')
    work_absence = fields.Float('Personal Emergency Absence', help="Absence due to a personal emergency.")
    unpaid_personal_care = fields.Float('Unpaid personal care', help="Unpaid personal care leave.")
    unpaid_candidacy = fields.Float('Unpaid candidacy leave', help="Unpaid leave for a political candidacy.")
    military_leave_absence =fields.Float('Military leave of absence', help="Absence for military service.")
    sunday_work_hours= fields.Float('Sunday work hours', help="Hours worked on Sunday")

    employee_lines = fields.One2many('info3.timesheet.wizard.line', 'timesheet_wizard_id', 'Employees')
    overwrite = fields.Boolean('Overwrite existing lines')

    @api.model
    def default_get(self, fields):
        """
        Timespan =
            - date if date is selected
            - false if no date is selected
        Employees = 
            - single employee if employee is selected
            - employees from single department if it is selected
            - all employees if no employee and no department is selected
        Analytic account = 
            - False if null (== no filter selected) or false (== 'No account' filter) is selected
            - account_id if single account is selected
        """
        context = self.env.context

        res = super(Info3TimesheetWizard, self).default_get(fields)
       
        if 'date' in context and context['date']:
            context_date = datetime.strptime(context['date'], DEFAULT_SERVER_DATE_FORMAT).date()
            res.update({
                'date': context['date'],
                'date_day': self.int_to_day(None, context_date),
                'date_to': context['date'],
                'date_to_day': self.int_to_day(None, context_date)
            })

        #TODO check if emp has already filled data in given date
        emp_obj = self.env['hr.employee']
        sheet_obj = self.env['info3.timesheet']
        # do not include emps who are managers of departments which don't allow managers adding themselves on the list
        invalid_emp_ids = self.get_invalid_emp_ids()
        employees_by_tag = emp_obj._get_employees_by_tag(include_inactive=True)

        emp_list = []
        emp_ids = []

        if context.get('current_analytic_account', False):
            res.update({'analytic_account_id': context['current_analytic_account']})

        #in case of empty list of employees, set emp_ids to empty list
        if 'employees' in context and context['employees'] == []:
            emp_ids = []
        elif 'current_employee' in context and context['current_employee'] != None:
            emp_ids = [context['current_employee']]
        elif 'employees' in context and len(context['employees']) > 0:
            # show only active empls
            for emp in context['employees']:
                emp_brw = emp_obj.browse(emp['id'])

                try:
                    emp_active = emp_brw.active
                except:
                    emp_active = True

                if emp_active and emp_brw.id not in invalid_emp_ids:
                    emp_ids.append(emp_brw.id)          
        else:                      
            # show only active empls
            emp_ids = emp_obj.search([('active', '=', True), ('id', 'not in', invalid_emp_ids), ('id', 'in', employees_by_tag.ids)]).ids
                    
        for emp_id in emp_ids:
            sheet_ids = sheet_obj.search([('employee_id','=',emp_id),('date','=',context['date'])])
            # only display emps that with given date are not already added
            if len(sheet_ids) == 0:
                emp_list.append({ 'employee_id': emp_id, 'filled_dates': '' })

        res.update({
            'employee_lines': [(0, 0, emp) for emp in emp_list]
        })
        return res

    def add_employees(self):
        wizard_obj = self.env['info3.timesheet.wizard']
        timesheet_obj = self.env['info3.timesheet']
        company_id = self.default_get(['company_id'])['company_id']
        overwrite = self.overwrite

        if not self.date or not self.date_to:
            return {'type': 'ir.actions.act_window_close'}

        warning_emps = {} #emp_name: [date1, date2...]

        values = {
            'employee_id': 0, #update in iteration 
            'department_id': 0, #update in iteration 
            'date': '', #update in iteration
            'start_time': self.start_time,  
            'end_time': self.end_time, 
            'annual_leave_hours': self.annual_leave_hours,  
            'total': self.total,  
            'night_work': self.night_work, 
            'overtime': self.overtime, 
            'holiday': self.holiday,
            'sick_leave': self.sick_leave,
            'maternity_leave': self.maternity_leave,
            'paternity_leave': self.paternity_leave,
            'parental_leave': self.parental_leave,
            'fieldwork': self.fieldwork,
            'fieldwork_abroad': self.fieldwork_abroad,
            'non_working_holiday': self.non_working_holiday,
            'non_working_sunday': self.non_working_sunday,
            'sick_leave_fund': self.sick_leave_fund,
            'paid_leave': self.paid_leave,
            'analytic_account_id': self.analytic_account_id.id if self.analytic_account_id.id else False,
            'sunday_work_hours': self.sunday_work_hours,

            'company_id': company_id
        }
        
        #each employee in self
        for line in self.employee_lines:

            #for given date range check and create new entry
            for d in self.daterange(self.date, self.date_to):
                
                date = d.strftime('%Y-%m-%d')
                emp_id = line.employee_id.id

                exist = timesheet_obj.search([('employee_id', '=', emp_id), ('date', '=', date)])
                
                if len(exist):
                    if emp_id not in warning_emps: warning_emps[emp_id] = []
                    warning_emps[emp_id].append(date)
                    if overwrite == True:
                        exist.unlink()

                values.update({
                    'employee_id': emp_id, 
                    'department_id': line.employee_id.department_id.id, 
                    'date': date
                })
                if (len(exist) > 0 and overwrite) or (len(exist) == 0):
                    timesheet_obj.create(values)
        return {
            'type': 'ir.actions.act_window_close',
            'warning': {'title':'warning', 'message':'Your message'},
            #'warning': str(warning_emps)
        }


    # employee control (if emp is filled in given date span exclude him)
    @api.onchange('date','date_to')
    def onchange_date(self):
        date_from = self.date
        date_to = self.date_to
        context = self.env.context
        if not date_from or not date_to: #when day is not selected wizard is empty!
            if date_from: return { 'value': { 'date_to': date_from } }
            elif date_to: return { 'value': { 'date': date_to } }
            else: return {}

        d_from = date_from
        d_to = date_to
        diff = (d_to - d_from).days

        if diff > 6:
            d_to = (d_from + timedelta(days=6))

        elif diff < 0:
            d_to = d_from

        emp_obj = self.env['hr.employee']
        sheet_obj = self.env['info3.timesheet']
        invalid_emp_ids = self.get_invalid_emp_ids()
        employees_by_tag = emp_obj._get_employees_by_tag(include_inactive=True)
        
        employee_lines = []

        try:
            if context['current_employee'] and context['current_employee'] != None:
                emp_ids = [context['current_employee']]
            elif context['department_id']:
                emp_ids = emp_obj.search([('department_id', '=', context['department_id']), ('active', '=', True), ('id', 'not in', invalid_emp_ids)]).ids
            else:
                emp_ids = emp_obj.search([('active', '=', True), ('id', 'not in', invalid_emp_ids), ('id', 'in', employees_by_tag.ids)]).ids
        except:
            emp_ids = emp_obj.search([('department_id', '=', context['department_id']), ('id', 'not in', invalid_emp_ids), ('id', 'in', employees_by_tag.ids)]).ids

        for emp_id in emp_ids:
            time_ids = sheet_obj.search([  ('employee_id', '=', emp_id),
                                            ('date', '>=', d_from.strftime('%Y-%m-%d')),
                                            ('date', '<=', d_to.strftime('%Y-%m-%d')) ]).ids

            #emp has no entries in given date span, add
            if len(time_ids) == 0:
                employee_lines.append({ 'employee_id': emp_id, 'filled_dates': '' })

            #emp has some entries, check which
            else:
                filled_dates = ''
                for entry in sheet_obj.browse(time_ids):
                    filled_dates += self.date_format(entry.date) + " (" + self.int_to_day(None, entry.date) + "), "
                employee_lines.append({ 'employee_id': emp_id, 'filled_dates': filled_dates[:-2] })

        self.date_to = datetime.strftime(d_to,DEFAULT_SERVER_DATE_FORMAT)
        self.date_to_day = self.int_to_day(d_to.weekday(), False)
        self.date_day = self.int_to_day(d_from.weekday(), False)

        self.employee_lines = [(5, 0, 0)] + [(0, 0, line) for line in employee_lines]



    def get_invalid_emp_ids(self):
        """return ids of employees who are managers of departments which don't allow managers to add themselves on timesheet"""
        emp_obj = self.env['hr.employee']
        user_emp_ids = emp_obj.search([('active', '=', True), ('user_id', '=', self.env.uid), ('department_id.manager_add_on_timesheet', '=', False)])
        invalid_emp_ids = []
        for emp in user_emp_ids:
            is_manager = (emp.department_id and emp.department_id.manager_id and emp.department_id.manager_id.id == emp.id)
            if is_manager:
                invalid_emp_ids.append(emp.id)
        return invalid_emp_ids

#     #for given integer converts to day string
    def int_to_day(self, int_day, format_day):
        string_day = ''

        if not int_day and int_day != 0 and format_day:
            int_day = format_day.weekday()

        if int_day == 0: string_day = _monday
        elif int_day == 1: string_day = _tuesday
        elif int_day == 2: string_day = _wednesday
        elif int_day == 3: string_day = _thursday
        elif int_day == 4: string_day = _friday
        elif int_day == 5: string_day = _saturday
        elif int_day == 6: string_day = _sunday

        return string_day


    def date_format(self, date_before):
        split = datetime.strftime(date_before, DEFAULT_SERVER_DATE_FORMAT).split('-')
        return split[2] + '.' + split[1]

    def daterange(self, d1, d2):
        return (d1 + timedelta(days=i) for i in range((d2 - d1).days + 1))

    @api.onchange('start_time', 'end_time')
    def onchange_start_end_time(self):
        self.total = self.end_time - self.start_time

    @api.onchange(
        'total',
        'non_working_sunday',
        'non_working_holiday',
        'annual_leave_hours',
        'night_work',
        'overtime',
        'holiday',
        'sick_leave',
        'sick_leave_fund',
        'fieldwork',
        'fieldwork_abroad',
        'maternity_leave',
        'paternity_leave',
        'parental_leave',
        'paid_leave',
        'start_time',
        'end_time'
    )
    def onchange_update_total_time(self):
        """
        We send data as a dict for easier calculation, in this case to sum keys from timesheet config file.
        All data from info3.timesheet.wizard is sent, we do not consider if it used or not - to make overrides in calculation easier.
        """
        ts_obj = self.env['info3.timesheet']
        total_hours = ts_obj.calculate_total_time(ts_obj._prepare_hours_dict(self))
        self.total = total_hours


class Info3TimesheetWizardLine(models.TransientModel):
    _name = "info3.timesheet.wizard.line"
    _description = "Employee line for timesheet wizard"

    employee_id = fields.Many2one('hr.employee', 'Employees')
    filled_dates = fields.Char('Filled dates', default='')
    timesheet_wizard_id = fields.Many2one('info3.timesheet.wizard', 'Timesheet wizard id')
