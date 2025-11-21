# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import date,datetime
from . import timesheet_common as TIMECOM
import calendar


class Info3Timesheet(models.Model):
    _name = 'info3.timesheet'
    _description = 'Timesheet'
    
    employee_id = fields.Many2one('hr.employee', "Employee", required=True)
    employee_category_ids = fields.Many2many(related='employee_id.category_ids')
    employee_active = fields.Boolean(related='employee_id.active')
    department_id = fields.Many2one('hr.department', 'Department', required=True)
    manager_id = fields.Many2one(related="department_id.manager_id", string="Manager")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('travel.order'),
        index=True)
    date = fields.Date('Date', required=True)

    start_time = fields.Float('Start of work')
    end_time = fields.Float('End of work')
    total = fields.Float('Total hours')

    outage = fields.Float('Outage hours', help="Time and hours of downtime, outages, etc..")
    night_work = fields.Float('Night work hours', help="Hours of work at night")
    overtime = fields.Float('Overtime work hours', help="Overtime hours")
    holiday = fields.Float('Holiday', help="Holiday")
    rescheduled_hours = fields.Float('Rescheduled hours', help="Hours of work in rescheduled working time")
    non_working_holiday = fields.Float('Non-working holiday hours', help="Hours of work on non-working holiday")
    non_working_sunday = fields.Float('Non-working sunday hours', help="Hours of work on non-working sunday")
    business_trip = fields.Float('Business trip hours', help="Hours spend on business trip")
    fieldwork = fields.Float('Fieldwork hours', help="Hours of field work")
    standby_hours = fields.Float('Standby hours', help="Standby hours and hours of work per call")
    annual_leave_hours = fields.Float('Annual leave hours', help="Hours of annual leave")
    sick_leave = fields.Float('Sick leave hours', help="Hours of sick leave paid by company")
    sick_leave_fund = fields.Float('Sick leave fund hours', help="Hours of sick leave paid by health insurance fund")
    maternity_leave = fields.Float('Maternity leave hours', help="Hours of maternity leave")
    paternity_leave = fields.Float('Paternity leave hours', help="Hours of paternity leave")
    parental_leave = fields.Float('Parental leave hours', help="Hours of parental leave")
    paid_leave = fields.Float('Paid leave hours', help="Hours of paid leave")
    unpaid_leave = fields.Float('Unpaid leave hours', help="Hours of unpaid leave")
    absence = fields.Float('Absence on worker request', help="Absence hours during the daily schedule demanded by worker")
    strike = fields.Float('Strike hours', help="Hours spent on strike")
    lockout = fields.Float('Lockout', help="Lockout hours")

    absence_fault = fields.Float('Absence by worker fault', help="Absence hours during the daily schedule faultet by worker.")
    daily_rest = fields.Float('Daily rest', help="Time of daily rest.")
    weekly_rest = fields.Float('Weekly rest', help="Time of weekly rest")
    other_maternity_leave = fields.Float('Other maternity leave', help="Other maternity leaves and rights")
    shift_work = fields.Float('Shift work', help="Shift hours")
    split_shift_work = fields.Float('Split shift work', help="Split shift work - shift that is splitted into two parts.")
    seconded_work = fields.Float('Seconded work', help="Hours of seconded work.")
    fieldwork_abroad = fields.Float('Fieldwork abroad', help="Hours of fieldwork abroad.")
    time_outage = fields.Text('Outage time', help="Time when outages started")
    work_absence = fields.Float('Personal Emergency Absence', help="Absence due to a personal emergency.")
    unpaid_personal_care = fields.Float('Unpaid personal care', help="Unpaid personal care leave.")
    unpaid_candidacy = fields.Float('Unpaid candidacy leave', help="Unpaid leave for a political candidacy.")
    military_leave_absence =fields.Float('Military leave of absence', help="Absence for military service.")
    analytic_account_id = fields.Many2one('account.analytic.account', "Analytic account")
    sunday_work_hours = fields.Float(help="Hours worked on sunday")

    @api.model
    def default_get(self, fields):
        res = super(Info3Timesheet, self).default_get(fields)
        context = self.env.context
        if 'employee_id' in context:
            res.update({'employee_id': context['employee_id']})
        if 'date' in context:
            res.update({'date': context['date']})
        return res

    def get_children_by_analytic_account(self, acc_ids):
        """
        Get all children for every analytic account.
        """
        acc_obj = self.env['account.analytic.account']
        data = {}
        for acc_id in acc_ids:
            acc_list = [acc_id]
            # child_acc_ids = acc_obj.search([('parent_id', '=', acc_id)])
            # while child_acc_ids:
            #     acc_list += child_acc_ids.ids
            #     child_acc_ids = acc_obj.search([('parent_id', 'in', child_acc_ids)])
            data[acc_id] = acc_list
        return data

    @api.model
    def list_analytic_accounts(self):
        """
        Return list of analytic accounts for filtering.
        """
        acc_obj = self.env['account.analytic.account']
        acc_list = [{'id': False, 'name': 'Bez konta'}]
        acc_ids = acc_obj.search([])
        acc_list += [{ 'id': acc.id, 'name': acc.name} for acc in acc_ids]
        acc_list_with_children = self.get_children_by_analytic_account(acc_ids.ids)
        data = {
            'account_list': acc_list,
            'account_list_with_children': acc_list_with_children,
        }
        return data

    def _prepare_result_employees(self, employees):
        result = list()
        for employee in employees:
            result.append({
                'id': employee.id,
                'name': employee.name,
                'active': employee.active,
                'department_id': employee.department_id.id
            })
        return result

    @api.model
    def list_employees(self):
        domain = []

        if self._context.get('department_id'):
            domain.append(('department_id', '=', self._context.get('department_id')))
        #else:
        #    domain.append(('department_id','=', 0))

        employee_obj = self.env['hr.employee']
        # return both active and inactive employees, later show/hide them with JS
        domain.append('|')
        domain.append(('active', '=', False))
        domain.append(('active', '=', True))
        employees = employee_obj.search(domain)
        result = self._prepare_result_employees(employees)
        return result

    @api.model
    def list_department_employees(self, day, month, year, department_id, employees):
        date = datetime.now()
        domain = [('department_id', '=', department_id)]
        employee_ids = [emp['id'] for emp in employees]

        if year:
            if month:
                if day:
                    domain.append(('date', '=', f'{year}-{month:02d}-{day:02d}'))
                else:
                    domain.extend([
                        ('date', '>=', f'{year}-{month:02d}-01'),
                        ('date', '<=', f'{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}')
                    ])
            else:
                domain.extend([
                    ('date', '>=', f'{year}-01-01'),
                    ('date', '<=', f'{year}-12-31')
                ])

        timesheet_records = self.env['info3.timesheet'].search(domain)
        filtered_list = []
        for tr in timesheet_records:
            info = [tr.employee_id.id,tr.employee_id.name,tr.employee_id.active,tr.department_id.id]
            if tr.employee_id.id not in employee_ids and info not in filtered_list:
                # filtering the list further in order to avoid duplicates
                filtered_list.append(info)
        result = filtered_list
        return result

    @api.model
    def list_departments(self):
        result = []
        employee_ids = []
        domain = []
        user_obj = self.env['res.users']
        user = user_obj.browse(self.env.uid)

        obj_data = self.env['ir.model.data']

        department_obj = self.env['hr.department']
        department_ids = department_obj.search(domain)

        for department in department_ids:
            result.append({
                'id': department.id,
                'name': department.name
            })

        return result

    @api.model
    def get_date_span(self):
        company_id = self.env['res.company']._company_default_get('info3.timesheet')
        ts_id = self.search([], order='date', limit=1) #get first used date

        if len(ts_id) > 0:
            firts_date = ts_id[0].date
            first_year = firts_date.year
        else:
            first_year = date.today().year

        days = [f"{i:02d}" for i in range(1, 32)]
        months = [f"{i:02d}" for i in range(1,13)]
        years = [i for i in range(first_year,date.today().year+2)]

        result = [days, months, years]
        return result

    @api.model
    def get_current_date(self):
        return {'day': f"{date.today().day:02d}", 'month': f"{date.today().month:02d}", 'year': date.today().year}
    
    def get_employee_times(self, emp_ids, date_from=None, date_to=None, sum=False):

        if len(emp_ids) == 0: return []

        #TODO test date formats!
        #TODO check for company_id
        domain = []
        if date_from != None and date_to != None:
            domain = [('date','>=',date_from),('date','<=',date_to),('employee_id','in',emp_ids)]
        elif date_from == None and date_to != None:
            domain = [('date','<=',date_to),('employee_id','in',emp_ids)]
        elif date_from != None and date_to == None:
            domain = [('date','>=',date_from),('employee_id','in',emp_ids)]
        else:
            domain = [('employee_id','in',emp_ids)]

        times = {} if sum else []

        time_ids = self.search(domain)
        res = time_ids.read([])
        if sum:
            field_work_days = 0
            field_work_abroad_days = 0
            for line in res:
                field_work_days = 0
                field_work_abroad_days = 0
                if 'fieldwork' in line and line['fieldwork'] != 0:
                    field_work_days +=1
                else:
                    field_work_days = 0
                if 'fieldwork_abroad' in line and line['fieldwork_abroad'] != 0:
                    field_work_abroad_days +=1
                else:
                    field_work_abroad_days = 0
                if line['employee_id'][0] not in times:
                    #add employee
                    times[line['employee_id'][0]] = {
                        'employee_id': line['employee_id'][0],
                        'employee_name': line['employee_id'][1],
                        'total': line['total'] if 'total' in line else 0,

                        'night_work': line['night_work'] if 'night_work' in line else 0,
                        'shift_work': line['shift_work'] if 'shift_work' in line else 0,
                        'holiday': line['holiday'] if 'holiday' in line else 0,
                        'standby_hours': line['standby_hours'] if 'standby_hours' in line else 0,
                        'non_working_day': line['non_working_day'] if 'non_working_day' in line else 0,
                        'rescheduled_hours': line['rescheduled_hours'] if 'rescheduled_hours' in line else 0,
                        'overtime': line['overtime'] if 'overtime' in line else 0,
                        'fieldwork_days': field_work_days,
                        'fieldwork_hours': line['fieldwork'] if 'fieldwork' in line else 0,
                        'outage': line['outage'] if 'outage' in line else 0,
                        'sick_leave': line['sick_leave'] if 'sick_leave' in line else 0,
                        'sick_leave_fund': line['sick_leave_fund'] if 'sick_leave_fund' in line else 0,
                        'paid_leave': line['paid_leave'] if 'paid_leave' in line else 0,
                        'maternity_leave': line['maternity_leave'] if 'maternity_leave' in line else 0,
                        'paternity_leave': line['paternity_leave'] if 'paternity_leave' in line else 0,
                        'parental_leave': line['parental_leave'] if 'parental_leave' in line else 0,
                        'annual_leave_hours': line['annual_leave_hours'] if 'annual_leave_hours' in line else 0,
                        'unpaid_leave': line['unpaid_leave'] if 'unpaid_leave' in line else 0,
                        'business_trip': line['business_trip'] if 'business_trip' in line else 0,
                        'lockout': line['lockout'] if 'lockout' in line else 0,
                        'strike': line['strike'] if 'strike' in line else 0,
                        'absence': line['absence'] if 'absence' in line else 0,
                        'seconded_work': line['seconded_work'] if 'seconded_work' in line else 0,                                                   
                        'fieldwork_abroad_days': field_work_abroad_days,
                        'fieldwork_abroad_hours': line['fieldwork_abroad'] if 'fieldwork_abroad' in line else 0,
                        'other_maternity_leave': line['other_maternity_leave'] if 'other_maternity_leave' in line else 0,
                        'absence_fault': line['absence_fault'] if 'absence_fault' in line else 0,
                        'isolation_hours': line['isolation_hours'] if 'isolation_hours' in line else 0,
                        'work_absence' : line['work_absence'] if 'work_absence' in line else 0,
                        'unpaid_personal_care': line['unpaid_personal_care'] if 'unpaid_personal_care' in line else 0,
                        'unpaid_candidacy': line['unpaid_candidacy'] if 'unpaid_candidacy' in line else 0,
                        'sunday_work_hours': line['sunday_work_hours'] if 'sunday_work_hours' in line else 0
                    }
                else:
                    #update employee times
                    times[line['employee_id'][0]]['total'] += (line['total'] if 'total' in line else 0)
                    times[line['employee_id'][0]]['night_work'] += (line['night_work'] if 'night_work' in line else 0)
                    times[line['employee_id'][0]]['shift_work'] += (line['shift_work'] if 'shift_work' in line else 0)
                    times[line['employee_id'][0]]['holiday'] += (line['holiday'] if 'holiday' in line else 0)
                    times[line['employee_id'][0]]['standby_hours'] += (line['standby_hours'] if 'standby_hours' in line else 0)
                    times[line['employee_id'][0]]['non_working_day'] += (line['non_working_day'] if 'non_working_day' in line else 0)
                    times[line['employee_id'][0]]['rescheduled_hours'] += (line['rescheduled_hours'] if 'rescheduled_hours' in line else 0)
                    times[line['employee_id'][0]]['overtime'] += (line['overtime'] if 'overtime' in line else 0)
                    times[line['employee_id'][0]]['fieldwork_days'] += field_work_days
                    times[line['employee_id'][0]]['fieldwork_hours'] += (line['fieldwork'] if 'fieldwork' in line else 0)
                    times[line['employee_id'][0]]['outage'] += (line['outage'] if 'outage' in line else 0)
                    times[line['employee_id'][0]]['sick_leave'] += (line['sick_leave'] if 'sick_leave' in line else 0)
                    times[line['employee_id'][0]]['sick_leave_fund'] += (line['sick_leave_fund'] if 'sick_leave_fund' in line else 0)
                    times[line['employee_id'][0]]['paid_leave'] += (line['paid_leave'] if 'paid_leave' in line else 0)
                    times[line['employee_id'][0]]['maternity_leave'] += (line['maternity_leave'] if 'maternity_leave' in line else 0)
                    times[line['employee_id'][0]]['paternity_leave'] += (line['paternity_leave'] if 'paternity_leave' in line else 0)
                    times[line['employee_id'][0]]['parental_leave'] += (line['parental_leave'] if 'parental_leave' in line else 0)
                    times[line['employee_id'][0]]['annual_leave_hours'] += (line['annual_leave_hours'] if 'annual_leave_hours' in line else 0)
                    times[line['employee_id'][0]]['unpaid_leave'] += (line['unpaid_leave'] if 'unpaid_leave' in line else 0)
                    times[line['employee_id'][0]]['business_trip'] += (line['business_trip'] if 'business_trip' in line else 0)
                    times[line['employee_id'][0]]['lockout'] += (line['lockout'] if 'lockout' in line else 0)
                    times[line['employee_id'][0]]['seconded_work'] += (line['seconded_work'] if 'seconded_work' in line else 0)
                    times[line['employee_id'][0]]['fieldwork_abroad_days'] += field_work_abroad_days
                    times[line['employee_id'][0]]['fieldwork_abroad_hours'] += (line['fieldwork_abroad'] if 'fieldwork_abroad' in line else 0)
                    times[line['employee_id'][0]]['strike'] += (line['strike'] if 'strike' in line else 0)
                    times[line['employee_id'][0]]['absence'] += (line['absence'] if 'absence' in line else 0)
                    times[line['employee_id'][0]]['absence_fault'] += (line['absence_fault'] if 'absence_fault' in line else 0)
                    times[line['employee_id'][0]]['other_maternity_leave'] += (line['other_maternity_leave'] if 'other_maternity_leave' in line else 0)
                    times[line['employee_id'][0]]['isolation_hours'] += (line['isolation_hours'] if 'isolation_hours' in line else 0)
                    times[line['employee_id'][0]]['work_absence'] += (line['work_absence'] if 'work_absence' in line else 0) 
                    times[line['employee_id'][0]]['unpaid_personal_care'] += (line['unpaid_personal_care'] if 'unpaid_personal_care' in line else 0)
                    times[line['employee_id'][0]]['unpaid_candidacy'] += (line['unpaid_candidacy'] if 'unpaid_candidacy' in line else 0)
                    times[line['employee_id'][0]]['sunday_work_hours'] += (line['sunday_work_hours'] if 'sunday_work_hours' in line else 0)


        else:
            #don't sum times, each line is added to array
            for line in res:
                if 'fieldwork' in line and line['fieldwork'] != 0:
                    field_work_days +=1
                else:
                    field_work_days = 0
                if 'fieldwork_abroad' in line and line['fieldwork_abroad'] != 0:
                    field_work_abroad_days +=1
                else:
                    field_work_abroad_days = 0

                obj = {
                        'employee_id': line['employee_id'][0],
                        'employee_name': line['employee_id'][1],
                        'total': line['total'] if 'total' in line else 0,

                        'night_work': line['night_work'] if 'night_work' in line else 0,
                        'shift_work': line['shift_work'] if 'shift_work' in line else 0,
                        'holiday': line['holiday'] if 'holiday' in line else 0,
                        'standby_hours': line['standby_hours'] if 'standby_hours' in line else 0,
                        'non_working_day': line['non_working_day'] if 'non_working_day' in line else 0,
                        'rescheduled_hours': line['rescheduled_hours'] if 'rescheduled_hours' in line else 0,
                        'overtime': line['overtime'] if 'overtime' in line else 0,
                        'fieldwork_days': field_work_days,
                        'fieldwork_hours': line['fieldwork'] if 'fieldwork' in line else 0,
                        'outage': line['outage'] if 'outage' in line else 0,
                        'sick_leave': line['sick_leave'] if 'sick_leave' in line else 0,
                        'sick_leave_fund': line['sick_leave_fund'] if 'sick_leave_fund' in line else 0,
                        'paid_leave': line['paid_leave'] if 'paid_leave' in line else 0,
                        'maternity_leave': line['maternity_leave'] if 'maternity_leave' in line else 0,
                        'paternity_leave': line['paternity_leave'] if 'paternity_leave' in line else 0,
                        'parental_leave': line['parental_leave'] if 'parental_leave' in line else 0,
                        'annual_leave_hours': line['annual_leave_hours'] if 'annual_leave_hours' in line else 0,
                        'unpaid_leave': line['unpaid_leave'] if 'unpaid_leave' in line else 0,
                        'business_trip': line['business_trip'] if 'business_trip' in line else 0,
                        'lockout': line['lockout'] if 'lockout' in line else 0,
                        'seconded_work': line['seconded_work'] if 'seconded_work' in line else 0,
                        'fieldwork_abroad_days': field_work_abroad_days,
                        'fieldwork_abroad_hours': line['fieldwork_abroad'] if 'fieldwork_abroad' in line else 0,
                        'strike': line['strike'] if 'strike' in line else 0,
                        'absence': line['absence'] if 'absence' in line else 0,
                        'absence_fault': line['absence_fault'] if 'absence_fault' in line else 0,
                        'other_maternity_leave': line['other_maternity_leave'] if 'other_maternity_leave' in line else 0,
                        'isolation_hours': line['isolation_hours'] if 'isolation_hours' in line else 0,
                        'work_absence': line['work_absence'] if 'work_absence' in line else 0,
                        'unpaid_personal_care': line['unpaid_personal_care'] if 'unpaid_personal_care' in line else 0,
                        'unpaid_candidacy': line['unpaid_candidacy'] if 'unpaid_candidacy' in line else 0,
                        'sunday_work_hours': line['sunday_work_hours'] if 'sunday_work_hours' in line else 0
                        }
                times.append(obj)

        return times

    @api.onchange('start_time', 'end_time')
    def onchange_start_end_time(self):
        self.total = max(self.end_time - self.start_time, 0)

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
        'end_time',
        'work_absence',
        'sunday_work_hours'
    )
    def onchange_update_total_time(self):
        """
        We send data as a dict for easier calculation, in this case to sum keys from timesheet config file.
        All data from info3.timesheet.wizard is sent, we do not consider if it used or not - to make overrides in calculation easier.
        """
        total_hours = self.calculate_total_time(self._prepare_hours_dict(self))
        self.total = total_hours

    def _prepare_hours_dict(self, model):
        """
        Read hours from either info3.timesheet or info3.timesheet.wizard to prepare for calculation.
        Field names need to be the same for each model for this to work.
        """
        hours_dict = {
            'total': model.total,
            'non_working_sunday': model.non_working_sunday,
            'non_working_holiday': model.non_working_holiday,
            'annual_leave_hours': model.annual_leave_hours,
            'night_work': model.night_work,
            'overtime': model.overtime,
            'holiday': model.holiday,
            'sick_leave': model.sick_leave,
            'sick_leave_fund': model.sick_leave_fund,
            'fieldwork': model.fieldwork,
            'fieldwork_abroad': model.fieldwork_abroad,
            'maternity_leave': model.maternity_leave,
            'paternity_leave': model.paternity_leave,
            'parental_leave': model.parental_leave,
            'paid_leave': model.paid_leave,
            'start_time': model.start_time,
            'end_time': model.end_time,
            'work_absence': model.work_absence,
            'sunday_work_hours': model.sunday_work_hours,
        }
        return hours_dict

    def calculate_total_time(self, hours_dict):
        """
        Default case: total = end_time - start_time.
        If one of other kinds of work_hours is entered, we reduce total by that amount (but it can not be less than 0:00).
        """
        total_hours = 0
        start_time = hours_dict['start_time']
        end_time = hours_dict['end_time']
        total = hours_dict['total']
        key_tuple = self.get_sum_hours_keys()
        sum_hours = sum([hours_dict[key] for key in key_tuple])
        if start_time and end_time:
            # this is the expected case - we use time diff as starting point because it is constant
            # if we used 'total' it would be reduced each time another field is changed
            if start_time <= end_time:
                #calculation if regular work
                total_hours = max(end_time - start_time - sum_hours, 0)
            else:
                total_hours = total
        elif total:
            # in case start and time are not entered, we reduce total hours anyway
            total_hours = max(total - sum_hours, 0)
        return total_hours
    
    def get_sum_hours_keys(self):
        return TIMECOM.get_categories()['timesheet_wizard_hours']
