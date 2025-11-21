# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import calendar
import math
from datetime import datetime,date
from operator import itemgetter
from ..models import timesheet_common as TIMECOM
import workdays
import icu

EMP_SORT_KEY = 'employee_name_sort'
LOCALE = 'hr_HR.utf8'

class HrBaseCommon:

    def _sort_with_collation(list_to_sort, key_to_sort_by, locale):
        """
        Sort list (of iterables) in custom locale.
        E.g. sorting list of croatian names / surnames:
            - by default names which begin with special croatian characters
              are after those that begin with 'z'
            - locale hr_HR.utf8 enables sorting the proper way,
              i.e. with characters in their croatian alphabetic order

        Args:
            list_to_sort (list): list of iterables (dict, tuple, list)
            key_to_sort_by (string or integer): iterable index
            locale (string): e.g. hr_HR.utf8

        Returns:
            list: list_to_sort sorted in given locale by key_to_sort_by
        """
        collator = HrBaseCommon._get_locale_collator(locale)
        sorted_list = sorted(list_to_sort, key=lambda x: collator.getSortKey(x[key_to_sort_by]))
        return sorted_list

    def _get_locale_collator(locale):
        return icu.Collator.createInstance(icu.Locale(locale))

class Info3TimesheetReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_timesheet.report_info3_timesheet'
    _description = 'Timesheet report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data['month'] or not data['year']:
            raise ValidationError(_("Mjesec i godina moraju biti odabrani!"))
        emp_obj = self.env['hr.employee']
        #variable to check report type
        sum_report = False
        report_lines = self.get_report_lines(data, sum_report)
        # a single emp_id is needed for the report to print
        emps = emp_obj.search([],limit=1)
        return {
            'doc_ids': emps.ids,
            'doc_model': 'hr.employee',
            'docs': emps,
            'report_lines': report_lines,
        }

    def get_report_lines(self, data, sum_report):
        emp_ts_dict = {}
        domain = []
        print_contract_area = data.get('print_contract_area',False)
        employee_ids= data.get('employee_ids', [])
        month = int(data['month'])
        year = int(data['year'])
        active_contract=False

        contract_date = date(year, month, 1) if year and month else fields.Date.context_today(self)
        first_day = date(contract_date.year, contract_date.month, 1)
        last_day_num = calendar.monthrange(contract_date.year, contract_date.month)[1]
        last_day = date(contract_date.year, contract_date.month, last_day_num)

        filtered_employee_ids = []
        binding_contract_ref = self.env.ref('l10n_hr_hr.hr_contract_area_type_2')
        for emp_id in employee_ids:
            consecutive_contracts = self.env['hr.employee'].browse(emp_id).get_consecutive_contracts(last_day)
            contracts = [c for c in consecutive_contracts if (c.date_end == False or c.date_end >= first_day) and c.date_start <= last_day]

            for contract in contracts:
                if (print_contract_area == 'employee' and contract.area == binding_contract_ref) or (print_contract_area == 'other' and contract.area != binding_contract_ref):
                    filtered_employee_ids.append(emp_id)
                    active_contract= contract
                    break

        if filtered_employee_ids:
            domain = [('employee_id', 'in', filtered_employee_ids)]  

        analytic_account_id = data.get('analytic_account', False)
        if analytic_account_id:
            domain.append(['analytic_account_id', '=', analytic_account_id])

        number_of_days_in_month = calendar.monthrange(year, month)[1]
        domain.append(['date','>=', str(year)+ '-' + str(month) + '-01'])
        domain.append(['date','<=', str(year) + '-' + str(month) + '-' + str(number_of_days_in_month)])

        ts_obj = self.env['info3.timesheet']
        ts_data = ts_obj.search(domain)
        

        if not ts_data or not filtered_employee_ids:
            raise ValidationError(_("Nema podataka za ispis!"))

        dict_list = {}
        for record in ts_data:
            key = record['employee_id'][0].id if record['employee_id'][0] else 0
            self.update_dict(dict_list,key, record,month,year,active_contract)

        for key in dict_list:
            emp_ts_dict.update({key: self.add_to_list(dict_list[key], sum_report)})
        
        for key in emp_ts_dict:
            for e in emp_ts_dict[key]['data']:
                if isinstance(e['day'], int):
                    e['day'] = self.get_date_string(e['day'], int(month), int(year))

        sorted_list = HrBaseCommon._sort_with_collation(emp_ts_dict.values(), EMP_SORT_KEY, LOCALE)
        return sorted_list

    def get_empty_ts_record(self, year, month):
        company_id = self.env['res.users'].browse(self.env.uid).company_id
        month = str(month)
        month = ('0' + month) if len(month) == 1 else month
        date = str(year) + '-' + month + '-' + '01'
        ts_record = [{
            'business_trip': 0.0, 'date': date, 'daily_rest': 0.0, 'other_maternity_leave': 0.0, 'total': 0.0, 'id': 0, 'non_working_sunday': 0.0, 'non_working_holiday': 0.0,
            'unpaid_leave': 0.0, 'rescheduled_hours': 0.0, 'company_id': (company_id.id, company_id.name), 'overtime': 0.0, 'absence': 0.0, 'manager_id': False,
            'strike': 0.0, 'holiday': 0.0, 'start_time': 0.0, 'department_id': ('', ''), 'seconded_work': 0.0, 'fieldwork': 0.0, 'outage': 0.0,
            'shift_work': 0.0, 'split_shift_work': 0.0, 'sick_leave': 0.0, 'sick_leave_fund': 0.0, 'employee_id': (0, ''), 'paid_leave': 0.0, 'standby_hours': 0.0, 'annual_leave_hours': 0.0,
            'fieldwork_abroad': 0.0, 'absence_fault': 0.0, 'weekly_rest': 0.0, 'time_outage': False, 'maternity_leave': 0.0, 'paternity_leave': 0.0,  'parental_leave': 0.0, 'lockout': 0.0, 'end_time': 0.0, 'night_work': 0.0,
            'work_absence':0.0,'unpaid_personal_care':0.0,'unpaid_candidacy':0.0,'military_leave_absence':0.0,'sunday_work_hours': 0.0,

        }]
        return ts_record

    def update_dict(self, emp_ts_list, id, record,year,month,active_contract):
        employee_by_contract = True if active_contract and active_contract.area == self.env.ref('l10n_hr_hr.hr_contract_area_type_2') else False
        if id not in emp_ts_list:
            emp = record.employee_id
            emp_ts_list.update({
                id: {
                    'employee_id': emp.id if emp else False,
                    'employee_name': emp._get_display_name_format('first_name_first').format(emp.first_name, emp.last_name),
                    'employee_name_sort': emp.name,
                    'department_id': record.department_id.id, 
                    'department_name': record.department_id.name,
                    'employee_by_contract': employee_by_contract,
                    'company_id': record.company_id.id, 
                    'job_title': self.get_job_title(record),
                    'company_name': record.company_id.name, 
                    'month': record.date.month,
                    'year': record.date.year,
                    'data': [self.add_object(record, record.date.day)]
                }
            })
        else:
            emp_ts_list[id]['data'].append(self.add_object(record, record.date.day))
     #create timesheet object
    def add_to_list(self, record, sum_report):

        #get number of days in month
        number_of_days_in_month = calendar.monthrange(int(record['year']), int(record['month']))[1]

        data_list = self.add_data_object_list(record['data'], number_of_days_in_month, sum_report)

        # converts time from 8.50 to 8:30
        conv_list = []
        for row in data_list:
            conv_obj = {}
            for key, val in row.items():
                if key != 'day' and key != 'time_outage': conv_obj[key] = self._float_time_convert(val)
                else: conv_obj[key] = val
            conv_list.append(conv_obj)
        avg_hours_per_day = self.get_avg_hours_per_day(record)
        
        # Calculate work hours
        start_date = datetime(record['year'], record['month'], 1)
        end_date = datetime(record['year'], record['month'], calendar.mdays[record['month']])
        holidays = self.env['hr.holiday'].search([('date', '>=', start_date), ('date', '<=', end_date)])
        holiday_dates = [h.date for h in holidays.filtered(lambda h: h.date.weekday()<5)]
        
        workday_diff = workdays.networkdays(start_date, end_date)
        number_of_working_days = workday_diff-len(holiday_dates)
        
        obj = {
            'employee_name': record['employee_name'],
            'employee_name_sort': record['employee_name_sort'],
            'department_name': record['department_name'],
            'job_title': record['job_title'],
            'employee_by_contract':record['employee_by_contract'],
            'company_name': record['company_name'],
            'month': record['month'],
            'year': record['year'],
            'data': conv_list,
            'avg_hours_per_day': avg_hours_per_day,
            'number_of_days': number_of_working_days,
            'number_of_hours': workday_diff*8,
        }
        return obj


    def add_data_object_list(self, records, num_of_days, sum_report):

        emp_ts = []
        list_of_days = []

        outage = 0
        total = 0
        night_work = 0
        overtime = 0
        holiday = 0

        daily_rest = 0
        weekly_rest = 0
        other_maternity_leave = 0
        absence_fault = 0
        split_shift_work = 0
        shift_work = 0

        rescheduled_hours = 0
        non_working_sunday = 0
        non_working_holiday = 0
        business_trip = 0
        fieldwork = 0
        standby_hours = 0
        annual_leave_hours = 0
        maternity_leave = 0
        paternity_leave = 0
        parental_leave = 0
        sick_leave = 0
        sick_leave_fund = 0
        paid_leave = 0
        unpaid_leave = 0
        absence = 0
        strike = 0
        lockout = 0
        fieldwork_abroad = 0
        time_outage = ''
        seconded_work = 0
        # used in info3_timesheet_report_sum
        hours_sum = 0
        work_absence =0
        unpaid_personal_care =0
        unpaid_candidacy=0
        military_leave_absence=0
        sunday_work_hours = 0

        total_hours = 0

        for key in records:
            if not sum_report:
                list_of_days.append(int(key['day']))
                emp_ts.append(self.add_object(key, int(key['day'])))

            outage += key['outage']
            total += key['total']
            night_work += key['night_work']
            overtime += key['overtime']
            holiday += key['holiday']

            daily_rest += key['daily_rest']
            weekly_rest += key['weekly_rest']
            absence_fault += key['absence_fault']
            split_shift_work += key['split_shift_work']
            shift_work += key['shift_work']
            other_maternity_leave += key['other_maternity_leave']

            rescheduled_hours += key['rescheduled_hours']
            non_working_sunday += key['non_working_sunday']
            non_working_holiday += key['non_working_holiday']
            business_trip += key['business_trip']
            fieldwork += key['fieldwork']
            standby_hours += key['standby_hours']
            annual_leave_hours += key['annual_leave_hours']
            maternity_leave += key['maternity_leave']
            paternity_leave += key['paternity_leave']
            parental_leave += key['parental_leave']
            sick_leave += key['sick_leave']
            sick_leave_fund += key['sick_leave_fund']
            paid_leave += key['paid_leave']
            unpaid_leave += key['unpaid_leave']
            absence += key['absence']
            strike += key['strike']
            lockout += key['lockout']
            fieldwork_abroad += key['fieldwork_abroad']
            time_outage = key['time_outage']
            seconded_work += key['seconded_work']
            work_absence += key['work_absence']
            unpaid_personal_care += key['unpaid_personal_care']
            unpaid_candidacy += key['unpaid_candidacy']
            military_leave_absence += key['military_leave_absence']
            sunday_work_hours += key['sunday_work_hours']
       #add empty days to list to
        if not sum_report:
            for i in range (1,num_of_days+1):
                if i not in list_of_days:
                    emp_ts.append(self.add_object(False, i))

            #sort list
            emp_ts = sorted(emp_ts, key=itemgetter('day'))

        #add sums to the end of the list
        emp_ts.append({
            'day': _('Ukupno'), 
            'start_time': 0, 
            'end_time': 0,
            'outage': outage,
            'total': total,
            'night_work': night_work,
            'overtime': overtime,
            'holiday': holiday,

            'daily_rest': daily_rest,
            'weekly_rest': weekly_rest,
            'other_maternity_leave': other_maternity_leave,
            'absence_fault': absence_fault,
            'shift_work': shift_work,
            'split_shift_work': split_shift_work,

            'rescheduled_hours': rescheduled_hours,
            'non_working_sunday': non_working_sunday,
            'non_working_holiday': non_working_holiday,
            'business_trip': business_trip,
            'fieldwork': fieldwork,
            'fieldwork_abroad': fieldwork_abroad,
            'standby_hours': standby_hours,
            'annual_leave_hours': annual_leave_hours,
            'maternity_leave': maternity_leave,
            'paternity_leave': paternity_leave,
            'parental_leave': parental_leave,
            'sick_leave': sick_leave,
            'sick_leave_fund': sick_leave_fund,
            'paid_leave': paid_leave,
            'unpaid_leave': unpaid_leave,
            'work_absence':work_absence,
            'unpaid_personal_care': unpaid_personal_care,
            'unpaid_candidacy': unpaid_candidacy,
            'military_leave_absence':military_leave_absence,
            'absence': absence,
            'strike': strike,
            'lockout': lockout,
            'time_outage':time_outage,
            'seconded_work': seconded_work,
            'sunday_work_hours': sunday_work_hours,
            'hours_sum': total + night_work + overtime + holiday + daily_rest + weekly_rest + other_maternity_leave + absence_fault + shift_work + split_shift_work + rescheduled_hours +
             non_working_sunday + non_working_holiday + business_trip + fieldwork + fieldwork_abroad + standby_hours + annual_leave_hours + maternity_leave + paternity_leave + sick_leave + sick_leave_fund + paid_leave + unpaid_leave + 
             absence + strike + lockout + seconded_work + parental_leave + work_absence + unpaid_personal_care + unpaid_candidacy + military_leave_absence + sunday_work_hours
        })

        work_hours_list = TIMECOM.get_categories()['work_hours']
        for key in work_hours_list:
            total_hours += emp_ts[-1][key]
        
        emp_ts[-1]['start_time'] = total_hours

        return emp_ts

    def add_object(self, record, day):
        return {
            'day': day,
            'start_time': record['start_time'] if record else 0, 
            'end_time': record['end_time'] if record else 0,
            'outage': record['outage'] if record else 0,
            'total': record['total'] if record else 0,
            'night_work': record['night_work'] if record else 0,
            'overtime': record['overtime'] if record else 0,
            'holiday': record['holiday'] if record else 0,

            'other_maternity_leave': record['other_maternity_leave'] if record else 0,
            'absence_fault': record['absence_fault'] if record else 0,
            'shift_work': record['shift_work'] if record else 0,
            'split_shift_work': record['split_shift_work'] if record else 0,

            'rescheduled_hours': record['rescheduled_hours'] if record else 0,
            'non_working_sunday': record['non_working_sunday'] if record else 0,
            'non_working_holiday': record['non_working_holiday'] if record else 0,
            'business_trip': record['business_trip'] if record else 0,
            'fieldwork': record['fieldwork'] if record else 0,
            'standby_hours': record['standby_hours'] if record else 0,
            'annual_leave_hours': record['annual_leave_hours'] if record else 0,
            'maternity_leave': record['maternity_leave'] if record else 0,
            'paternity_leave': record['paternity_leave'] if record else 0,
            'parental_leave': record['parental_leave'] if record else 0,
            'sick_leave': record['sick_leave'] if record else 0,
            'sick_leave_fund': record['sick_leave_fund'] if record else 0,
            'paid_leave': record['paid_leave'] if record else 0,
            'unpaid_leave': record['unpaid_leave'] if record else 0,
            'absence': record['absence'] if record else 0,
            'strike': record['strike'] if record else 0,
            'lockout': record['lockout'] if record else 0,
            'work_absence': record['work_absence'] if record else 0,
            'unpaid_personal_care': record['unpaid_personal_care'] if record else 0,
            'unpaid_candidacy': record['unpaid_candidacy'] if record else 0,
            'military_leave_absence':record['military_leave_absence'] if record else 0,
            'daily_rest': record['daily_rest'] if record else 0,
            'weekly_rest': record['weekly_rest'] if record else 0,
            'fieldwork_abroad': record['fieldwork_abroad'] if record else 0,
            'time_outage': record['time_outage'] if record else '',
            'seconded_work': record['seconded_work'] if record else 0,
            'sunday_work_hours': record['sunday_work_hours'] if record else 0,
        }


    #TODO option to translate?
    #returns shorter version for day for easier navigation
    def get_date_string(self, day, month, year):
        dt = datetime(year, month, day)
        c = dt.weekday()

        if c == 0: s = u'PO'
        elif c == 1: s = u'UT'
        elif c == 2: s = u'SR'
        elif c == 3: s = u'CE'
        elif c == 4: s = u'PE'
        elif c == 5: s = u'SU'
        else: s = u'NE'

        if day < 10: day = "0" + str(day)
        else: day = str(day)

        if month < 10: month = "0" + str(month)
        else: month = str(month)
        
        return day + "." + month + "  " + s

    # return time as "05:30" from 5.5
    def _float_time_convert(self, float_val):
        if float_val == 0: return ''
        factor = float_val < 0 and -1 or 1
        val = abs(float_val)
        return '%02d:%02d' % (factor * int(math.floor(val)), int(round((val % 1) * 60)))

    # used in info3_timesheet_report_sum
    def get_avg_hours_per_day(self, record):
        avg_hours_per_day = 0
        day = calendar.monthrange(record['year'], record['month'])[1]
        formated_date = f"{record['year']}-{record['month']}-{day}"
        self.env.cr.execute("""SELECT day_hours FROM hr_salary_parameters WHERE employee_id = {0} AND date_from <= '{1}'::date 
                            ORDER BY date_from DESC LIMIT 1""".format(record['employee_id'], formated_date))
        res = self.env.cr.fetchall()
        return self._float_time_convert(avg_hours_per_day)

    def get_job_title(self, record):
        day = calendar.monthrange(record.date.year, record.date.month)[1]
        formated_date = f"{record.date.year}-{record.date.month}-{day}"
        self.env.cr.execute("""SELECT job_id FROM hr_salary_parameters WHERE employee_id = {0} AND date_from <= '{1}'::date 
                            ORDER BY date_from DESC LIMIT 1""".format(record.employee_id.id, formated_date))
        res_job_id = self.env.cr.fetchall()
        job_name = ''
        if res_job_id:
            job_name = self.env['hr.job'].search([('id', '=', res_job_id[0][0])]).name
        return job_name
