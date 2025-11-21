# -*- coding: utf-8 -*-

from re import S
from odoo import api, models, _
import time
from datetime import datetime, timedelta
import pytz
from datetime import datetime
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from ..models import payroll_common as paycom


class WorkStatisticsReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_work_statistics'
    _description = 'Work statistics report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date = data['date']

        docargs = {
            'company': self.env.user.company_id,
            'employment_data': self.get_employment_data(date),
            'work_type': self.get_work_type(date),
            'worktime_type': self.get_worktime_type(date),
            'salaries': self.get_salaries(date),
            'employee_by_age': self.get_employee_by_age(date),
            'education': self.get_education(date),
            'employee_hours': self.employee_hours(date),
            'settlement_of_work': self.settlement_of_work(date),
            'yearly_salary': self.get_yearly_salary(date),
            'period': self.return_period(date),
            'last_date': self.return_last_date(date),
            'year_before': self.return_year_before(date),
        }
        return {
            'data': docargs,
        }

    # go through every employee and check if their first contract starts or last contract ends in selected period
    # write contract, employee and gender for each category because this data is most commonly needed
    def get_employees(self, date):
        employee_obj = self.env['hr.employee']

        date_first = datetime.strptime(date[:-2] + '01', DEFAULT_SERVER_DATE_FORMAT).date()
        date_last_left = date_first + relativedelta(months=+1, days=-1)
        date_before = date_first + relativedelta(days=-1)

        employees = employee_obj.search(
            ['|', ('active', '=', True),
             ('active', '=', False),
             ('is_employee', '=', True)])
        female_emp_ids = employee_obj.search(
            [('gender', '=', 'female'),
             '|', ('active', '=', True),
             ('active', '=', False),
             ('is_employee', '=', True)])
        emp_before = []
        emp_arrived = []
        emp_left = []
        emp_after = []

        for emp in employees:
            emp_period_contract_list = emp.get_consecutive_contracts(date_last_left)
            if not emp_period_contract_list:  # employee wasnt employed yet
                continue
            emp_first_contract = emp_period_contract_list[0]
            emp_last_contract = emp_period_contract_list[-1]

            if emp_first_contract.date_start <= date_before and (
                    not emp_last_contract.date_end or emp_last_contract.date_end >= date_before):
                emp_before.append({'employee_id': emp.id, 'contract_id': emp_last_contract.id,
                                  'female': True if emp.id in female_emp_ids.ids else False})

            if emp_first_contract.date_start >= date_first and emp_first_contract.date_start <= date_last_left:
                emp_arrived.append({'employee_id': emp.id, 'contract_id': emp_last_contract.id,
                                   'female': True if emp.id in female_emp_ids.ids else False})

            termination_cond = emp_last_contract.termination_date and (
                emp_last_contract.termination_date >= date_before and emp_last_contract.termination_date < date_last_left)
            end_date_cond = self.is_last_contract(
                emp_last_contract) and emp_last_contract.date_end and emp_last_contract.date_end >= date_before and emp_last_contract.date_end < date_last_left
            if termination_cond or end_date_cond:
                emp_left.append({'employee_id': emp.id, 'contract_id': emp_last_contract.id,
                                'female': True if emp.id in female_emp_ids.ids else False})

        for el in emp_before:
            emp_after.append(el)
        for el in emp_arrived:
            emp_after.append(el)
        for el in emp_left:
            emp_after.remove(el)
        return {
            'on_date': emp_before,
            'arrived': emp_arrived,
            'left': emp_left,
            'after': emp_after,
        }

    def get_employment_data(self, date):
        date_first = date[:-2] + '01'
        date_before = (datetime.strptime(date_first, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=-1)
                       ).strftime(DEFAULT_SERVER_DATE_FORMAT)
        month = datetime.strptime(date_first, DEFAULT_SERVER_DATE_FORMAT).month

        data = []
        res = self.get_employees(date)
        employees_on_date = len(res['on_date'])
        employees_arrived = len(res['arrived'])
        employees_left = len(res['left'])
        women_on_date = len([x for x in res['on_date'] if x['female'] == True])
        women_arrived = len([x for x in res['arrived'] if x['female'] == True])
        women_left = len([x for x in res['left'] if x['female'] == True])

        state_employee = employees_on_date + employees_arrived - employees_left
        state_woman = women_on_date + women_arrived - women_left

        data.extend(
            [{'description': _(u"Number of employees on ") + (datetime.strptime(date_before, '%Y-%m-%d')).strftime(
                '%d.%m.%Y'),
              'total': str(employees_on_date),
              'women': str(women_on_date)},
             {'description': _(u"Arrived during {0}. month").format(month),
              'total': str(employees_arrived),
              'women': str(women_arrived)},
             {'description': _(u"Left during {0}. month").format(month),
              'total': str(employees_left),
              'women': str(women_left)},
             {'description': _(u"Number of employees at the end of {0}. month").format(month),
              'total': str(state_employee),
              'women': str(state_woman)}, ])
        return data

    # last contract is one that doesn't have a consecutive contract, meaning:
    # - there aren't any after it
    # - it has end date and the next contract either doesn't exist or has start_date that isn't immediately after
    def is_last_contract(self, current_contract):
        contract_obj = self.env['hr.contract']
        # get all contracts starting after the one we got
        contracts = contract_obj.search(
            [('employee_id', '=', current_contract.employee_id.id),
             ('date_start', '>', current_contract.date_start)],
            order='date_start ASC')
        if not contracts:  # current contract is last because there arent any after it
            return True
        if contracts and not current_contract.date_end:  # there is a following contract and it is considered consecutive because current contract doesn't end
            return False
        comparison_contract = contracts[0]
        if comparison_contract.date_start == (current_contract.date_end + relativedelta(days=+1)):
            return False  # consecutive by the book
        # we declare the contract - last (in current sequence, because it has end_date and then a break until next contract)
        return True

    def get_work_type(self, date):
        cr = self._cr
        after_list = self.get_employees(date)['after']
        contract_ids = [x['contract_id'] for x in after_list]
        female_contract_ids = [x['contract_id'] for x in after_list if x['female'] == True]
        
        sql = """
            SELECT hcs.id AS area_id, hcs.name AS area_name, count(*) as count, 'total' as type FROM hr_contract hc
            LEFT JOIN hr_contract_subarea_type hcs ON hcs.id = hc.area_type
            WHERE hc.id = ANY(%s) GROUP BY hcs.id
            UNION ALL
            SELECT hcs.id AS area_id, hcs.name AS area_name, count(*) as count, 'women' as type FROM hr_contract hc
            LEFT JOIN hr_contract_subarea_type hcs ON hcs.id = hc.area_type
            WHERE hc.id = ANY(%s) GROUP BY hcs.id
        """

        res_dict = {}
        cr.execute(sql, (contract_ids, female_contract_ids))
        result = cr.dictfetchall()
        for row in result:
            if row['area_id'] not in res_dict:
                res_dict[row['area_id']] = {
                    'description': row['area_name'],
                    'total': 0,
                    'women': 0,
                }
            for row_type in ('total', 'women'):
                if row['type'] == row_type:
                    res_dict[row['area_id']][row_type] += row['count']

        return sorted([value for _, value in res_dict.items()], key=lambda k: k['total'], reverse=True)

    def get_worktime_type(self, date):
        cr = self._cr
        last_date = (datetime.strptime(
            date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(months=+1, days=-1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        after_list = self.get_employees(date)['after']
        contract_ids = [x['contract_id'] for x in after_list]
        female_contract_ids = [x['contract_id'] for x in after_list if x['female'] == True]
        joppd_b9_sel = self.env['hr.joppd.form.b']._b9_sel()
        joppd_b9_dict = {item[0]: item[1] for item in joppd_b9_sel}
        
        sql = """
            SELECT hsp.joppd_b9 AS joppd_b9, count(*) as count, 'total' as type FROM hr_contract hc
            LEFT JOIN hr_salary_parameters hsp on hsp.contract_id = hc.id
            WHERE hc.id = ANY(%(contract_ids)s) AND hsp.date_from <= %(last_date)s AND (hsp.date_to >= %(last_date)s or hsp.date_to is null) GROUP BY hsp.joppd_b9
            UNION ALL
            SELECT hsp.joppd_b9 AS joppd_b9, count(*) as count, 'women' as type FROM hr_contract hc
            LEFT JOIN hr_salary_parameters hsp on hsp.contract_id = hc.id
            WHERE hc.id = ANY(%(female_contract_ids)s) AND hsp.date_from <= %(last_date)s AND (hsp.date_to >= %(last_date)s or hsp.date_to is null) GROUP BY hsp.joppd_b9
        """

        res_dict = {}
        cr.execute(sql, {
            'contract_ids': contract_ids,
            'female_contract_ids': female_contract_ids,
            'last_date': last_date
        })
        result = cr.dictfetchall()
        for row in result:
            if row['joppd_b9'] not in res_dict:
                res_dict[row['joppd_b9']] = {
                    'description': row['joppd_b9'] in joppd_b9_dict and joppd_b9_dict[row['joppd_b9']],
                    'total': 0,
                    'women': 0,
                }
            for row_type in ('total', 'women'):
                if row['type'] == row_type:
                    res_dict[row['joppd_b9']][row_type] += row['count']

        return sorted([value for _, value in res_dict.items()], key=lambda k: k['total'], reverse=True)

    def get_salaries(self, date):
        cr = self._cr
        date_first = date[:-2] + '01'
        date_first = (datetime.strptime(date_first, '%Y-%m-%d') + relativedelta(months=+1)).strftime('%Y-%m-%d')
        date_last = (datetime.strptime(date_first, '%Y-%m-%d') + relativedelta(months=+1, days=-1)).strftime('%Y-%m-%d')

        sql = """SELECT SUM(line.amount) AS amount
                    FROM hr_payslip_run run
                    LEFT JOIN hr_payslip payslip ON payslip.payslip_run_id = run.id
                    LEFT JOIN hr_payslip_line line ON line.slip_id = payslip.id
                    LEFT JOIN hr_employee employee ON employee.id = payslip.employee_id 
                    WHERE line.code = 'NETO' AND run.pay_date >= '{0}' AND run.pay_date <= '{1}'
                    AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
                    GROUP BY employee.id""".format(date_first, date_last)
        cr.execute(sql)
        result = cr.fetchall()

        order = {
            '-3400': 0,
            '3401-3700': 1,
            '3701-4000': 2,
            '4001-4500': 3,
            '4501-5000': 4,
            '5001-5500': 5,
            '5501-6000': 6,
            '6001-8000': 7,
            '8001-10000': 8,
            '10001-12000': 9,
            '12001-14000': 10,
            '14001-16000': 11,
            '16001-21000': 12,
            '21001-': 13,
        }

        data = {
            '-3400': 0,
            '3401-3700': 0,
            '3701-4000': 0,
            '4001-4500': 0,
            '4501-5000': 0,
            '5001-5500': 0,
            '5501-6000': 0,
            '6001-8000': 0,
            '8001-10000': 0,
            '10001-12000': 0,
            '12001-14000': 0,
            '14001-16000': 0,
            '16001-21000': 0,
            '21001-': 0,
        }
        result_list = []
        for el in result:
            if el[0] <= 3400:
                data['-3400'] += 1
            elif el[0] >= 3401 and el[0] <= 3700:
                data['3401-3700'] += 1
            elif el[0] >= 3701 and el[0] <= 4000:
                data['3701-4000'] += 1
            elif el[0] >= 4001 and el[0] <= 4500:
                data['4001-4500'] += 1
            elif el[0] >= 4501 and el[0] <= 5000:
                data['4501-5000'] += 1
            elif el[0] >= 5001 and el[0] <= 5500:
                data['5001-5500'] += 1
            elif el[0] >= 5501 and el[0] <= 6000:
                data['5501-6000'] += 1
            elif el[0] >= 6001 and el[0] <= 8000:
                data['6001-8000'] += 1
            elif el[0] >= 8001 and el[0] <= 10000:
                data['8001-10000'] += 1
            elif el[0] >= 10001 and el[0] <= 12000:
                data['10001-12000'] += 1
            elif el[0] >= 12001 and el[0] <= 14000:
                data['12001-14000'] += 1
            elif el[0] >= 14001 and el[0] <= 16000:
                data['14001-16000'] += 1
            elif el[0] >= 16001 and el[0] <= 21000:
                data['16001-21000'] += 1
            elif el[0] > 21000:
                data['21001-'] += 1
        for el in data:
            result_list.append({'description': el, 'total': data[el], 'order': order[el]})
        result = sorted(result_list, key=lambda k: k['order'])
        return result

    def get_yearly_salary(self, date):
        cr = self._cr
        result_gender = []
        date_start = str(int(date[:4]) - 1) + '-01-01'
        date_end = str(int(date[:4]) - 1) + '-12-31'
        emps_whole_year = """    
            SELECT emp.id
            FROM hr_employee AS emp
            JOIN hr_payslip AS slip ON slip.employee_id = emp.id
            -- this join is used to count total number of salary payments made
            -- we need to filter out salary_in_kind, only_inputs, profit_payment and annual_calculation
            JOIN (SELECT emp.id AS emp_id, count(emp.id) AS number
                FROM hr_payslip AS slip
                JOIN hr_employee AS emp ON emp.id = slip.employee_id
                JOIN hr_payslip_run AS run ON run.id = slip.payslip_run_id
                WHERE (slip.date_from >= '{0}' AND slip.date_to <= '{1}')
                AND (run.i3_add_only_inputs != true OR run.i3_add_only_inputs IS NULL)
                AND (run.salary_in_kind = false OR run.salary_in_kind IS NULL)
                AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
                AND slip.annual_calculation = false
                GROUP BY emp.id) as slips_total on slips_total.emp_id = emp.id
            -- this join is used to confirm employee has a slip which begins on 01-01 and a slip which ends on 12-01
            -- which coupled with 12 slips in total should be enough to ensure employee has indeed been employed for the whole year
            JOIN (SELECT emp.id AS emp_id, count(emp.id) AS number
                FROM hr_payslip AS slip
                JOIN hr_employee AS emp ON emp.id = slip.employee_id
                JOIN hr_payslip_run AS run ON run.id = slip.payslip_run_id
                WHERE (slip.date_from = '{0}' OR slip.date_to = '{1}')
                AND (run.i3_add_only_inputs != true OR run.i3_add_only_inputs IS NULL)
                AND (run.salary_in_kind = false OR run.salary_in_kind IS NULL)
                AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
                AND slip.annual_calculation = false
                GROUP BY emp.id) as slips_jan_dec on slips_jan_dec.emp_id = emp.id
            WHERE slip.paid_date >= '{0}'
            AND slip.paid_date <= '{1}'
            AND slips_total.number = 12
            AND slips_jan_dec.number = 2
            GROUP BY emp.id""".format(date_start, date_end)

        cr.execute(emps_whole_year)
        res = cr.dictfetchall()
        employee_list = [x['id'] for x in res]

        total_neto = 0
        total_bruto = 0
        total_number = 0
        if len(employee_list) > 0:
            sql = """SELECT 
                        COALESCE(SUM(line_neto.amount), 0) AS neto,
                        COALESCE(SUM(line_bruto.amount), 0) AS bruto,
                        COUNT(DISTINCT employee.id) AS number,
                        --count(CASE WHEN (degree.id IS NOT Null) THEN 1 ELSE NULL END) AS number,
                        COALESCE(degree.name, '{3}') as name
                        FROM hr_payslip_run run
                        LEFT JOIN hr_payslip payslip on payslip.payslip_run_id = run.id
                        LEFT JOIN hr_payslip_line line_neto ON (line_neto.slip_id = payslip.id AND line_neto.code = 'NETO')
                        LEFT JOIN hr_payslip_line line_bruto ON (line_bruto.slip_id = payslip.id AND line_bruto.code = 'BASIC')
                        LEFT JOIN hr_employee employee ON employee.id = payslip.employee_id 
                        LEFT JOIN hr_employee_degree degree ON degree.id=employee.degree_id
                        WHERE run.pay_date > '{0}' AND run.pay_date < '{1}' AND employee.id IN {2}
                        AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
                        GROUP BY degree.name
                        """.format(date_start, date_end, paycom.get_ids_sql_condition(employee_list), _('None entered'))

            cr.execute(sql)

            result = cr.dictfetchall()
            sql_gender = """SELECT 
                        COALESCE(SUM(line_neto.amount), 0) AS neto,
                        COALESCE(SUM(line_bruto.amount), 0) AS bruto,
                        (CASE 
                            WHEN (employee.gender= 'male') THEN 'Muškarci' 
                            WHEN employee.gender= 'female' THEN 'Žene' 
                            WHEN employee.gender= 'other' THEN 'Ostalo'
                            ELSE '{3}' END) AS name,
                        COUNT(DISTINCT employee.id) AS number
                        FROM hr_payslip_run run
                        LEFT JOIN hr_payslip payslip ON payslip.payslip_run_id = run.id
                        LEFT JOIN hr_payslip_line line_neto ON (line_neto.slip_id = payslip.id AND line_neto.code = 'NETO')
                        LEFT JOIN hr_payslip_line line_bruto ON (line_bruto.slip_id = payslip.id AND line_bruto.code = 'BASIC')
                        LEFT JOIN hr_employee employee ON employee.id = payslip.employee_id                     
                        WHERE run.pay_date > '{0}' AND run.pay_date < '{1}' AND employee.id IN {2}  
                        AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
                        GROUP BY employee.gender
                        """.format(date_start, date_end, paycom.get_ids_sql_condition(employee_list), _('None entered'))
            cr.execute(sql_gender)
            result_gender = cr.dictfetchall()

            for el in result_gender:
                total_neto += el['neto']
                total_bruto += el['bruto']
                total_number += el['number']
            result_gender.extend(result)

        result_gender.insert(0, {'name': _(u'Total'), 'bruto': total_bruto,
                                'neto': total_neto, 'number': total_number})
        return result_gender

    def get_employee_by_age(self, date):
        cr = self._cr
        result_list = []
        date_first = date[:-2] + '01'
        date_last = (datetime.strptime(date_first, '%Y-%m-%d') + relativedelta(months=+1, days=-1)).strftime('%Y-%m-%d')

        on_date_ids = self.get_employees(date)['after']
        on_date_emp_ids = [x['employee_id'] for x in on_date_ids]
        on_date_female_emp_ids = [x['employee_id'] for x in on_date_ids if x['female'] == True]

        if len(on_date_emp_ids):
            employee_birth = """SELECT birthday FROM hr_employee WHERE id IN {0}""".format(
                paycom.get_ids_sql_condition(on_date_emp_ids))
            cr.execute(employee_birth)
            employee = cr.dictfetchall()
            employee_number = self.get_number_by_year(employee, date_last)

            women_number = False
            if on_date_female_emp_ids:
                women = """SELECT birthday FROM hr_employee WHERE id IN {0}""".format(
                    paycom.get_ids_sql_condition(on_date_female_emp_ids))
                cr.execute(women)
                women_birth = cr.dictfetchall()
                women_number = self.get_number_by_year(women_birth, date_last)

            for el in employee_number:
                if women_number and el in women_number:
                    result_list.append({'description': el, 'total': employee_number[el], 'women': women_number[el]})
                else:
                    result_list.append({'description': el, 'total': employee_number[el], 'women': 0})
        result = sorted(result_list, key=lambda k: k['description'])
        result = self.return_total(result)
        return result

    def get_number_by_year(self, birthdays, date):
        data = {}
        date = datetime.strptime(date, '%Y-%m-%d')
        data.update({'-19': 0, '19-24': 0, '25-29': 0, '30-34': 0, '35-39': 0,
                    '40-44': 0, '45-49': 0, '50-54': 0, '55-59': 0, '59-': 0})
        for el in birthdays:
            born = el['birthday']
            age = 0
            if born:
                age = date.year - born.year - ((date.month, date.day) < (born.month, born.day))

            if age < 19:
                if '-19' not in data:
                    data.update({'-19': 1})
                else:
                    data['-19'] += 1
            elif age >= 19 and age <= 24:
                if '19-24' not in data:
                    data.update({'19-24': 1})
                else:
                    data['19-24'] += 1
            elif age >= 25 and age <= 29:
                if '25-29' not in data:
                    data.update({'25-29': 1})
                else:
                    data['25-29'] += 1
            elif age >= 30 and age <= 34:
                if '30-34' not in data:
                    data.update({'30-34': 1})
                else:
                    data['30-34'] += 1
            elif age >= 35 and age <= 39:
                if '35-39' not in data:
                    data.update({'35-39': 1})
                else:
                    data['35-39'] += 1
            elif age >= 40 and age <= 44:
                if '40-44' not in data:
                    data.update({'40-44': 1})
                else:
                    data['40-44'] += 1
            elif age >= 45 and age <= 49:
                if '45-49' not in data:
                    data.update({'45-49': 1})
                else:
                    data['45-49'] += 1
            elif age >= 50 and age <= 54:
                if '50-54' not in data:
                    data.update({'50-54': 1})
                else:
                    data['50-54'] += 1
            elif age >= 55 and age <= 59:
                if '55-59' not in data:
                    data.update({'55-59': 1})
                else:
                    data['55-59'] += 1
            else:
                if '59-' not in data:
                    data.update({'59-': 1})
                else:
                    data['59-'] += 1

        return data

    def get_education(self, date):
        result = []
        on_date_ids = self.get_employees(date)['after']
        on_date_emp_ids = [x['employee_id'] for x in on_date_ids]
        if len(on_date_emp_ids):
            employee_degree = """SELECT COUNT(employee.id) AS total, COALESCE(degree.name, '{1}') AS description, count(employee_women.id) AS women
                                    FROM hr_employee employee
                                    LEFT JOIN hr_employee employee_women ON (employee_women.id = employee.id AND employee_women.gender = 'female')
                                    LEFT JOIN hr_employee_degree degree ON degree.id = employee.degree_id
                                    WHERE employee.id in {0} group by degree.name""".format(paycom.get_ids_sql_condition(on_date_emp_ids), _('None entered'))
            self._cr.execute(employee_degree)
            employee = self._cr.dictfetchall()
            result = sorted(employee, key=lambda k: k['description'])
        result = self.return_total(result)
        return result

    def employee_hours(self, date):
        cr = self._cr
        result_list = []
        done_hours = 0
        not_done_hours_company = 0
        not_paid_hours = 0
        not_done_hours_not_company = 0
        overtime_hours = 0
        number_of_months = 0
        total = 0
        average_employee = 0
        average_hours = 0
        run_obj = self.env['hr.payslip.run']
        date_start = str(int(date[:4]) - 1) + '-01-01'
        date_end = str(int(date[:4]) - 1) + '-12-31'
        payslip_runs = run_obj.search([('date_start', '>=', date_start), ('date_start', '<', date_end)])
        payslip_run_ids = payslip_runs.ids
        run_ids = paycom.get_ids_sql_condition(payslip_run_ids)
        if len(payslip_run_ids) > 0:
            # check earnings and bolovanje_fond in payroll_common.py
            payroll_conf = self.env['hr.payroll.salary.rule.configuration'] 
            worked = payroll_conf.get_rules('worked')
            not_worked_paid_by_company = payroll_conf.get_rules('not_worked_paid_by_company')
            not_worked_not_paid_by_company = payroll_conf.get_rules('not_worked_not_paid_by_company')
            not_paid = payroll_conf.get_rules.get('not_paid')
            overtime = payroll_conf.get_rules.get('overtime')
            params = {
                'worked': worked,
                'run_ids': run_ids,
            }
            string = """SELECT
                COALESCE(SUM(line.number_of_hours), 0)
                FROM hr_payslip_run AS run
                LEFT JOIN hr_payslip AS payslip ON payslip.payslip_run_id = run.id
                LEFT JOIN hr_payslip_worked_days AS line ON (line.payslip_id = payslip.id AND line.code IN %(worked)s)
                WHERE run.id IN %(run_ids)s"""

            cr.execute(sql, params)
            done_hours = cr.fetchone()[0]
            result_list.append({'description': _(u"Worked hours"), 'total': done_hours})

            sql = string.format(not_worked_paid_by_company, run_ids)
            cr.execute(sql)
            not_done_hours_company = cr.fetchone()[0]
            result_list.append({'description': _(u"Not worked hours paid by company"), 'total': not_done_hours_company})

            sql = string.format(not_worked_not_paid_by_company, run_ids)
            cr.execute(sql)
            not_done_hours_not_company = cr.fetchone()[0]
            result_list.append(
                {'description': _(u"Not worked hours paid outside company"),
                 'total': not_done_hours_not_company})

            sql = string.format(not_paid, run_ids)
            cr.execute(sql)
            not_paid_hours = cr.fetchone()[0]
            result_list.append({'description': _(u"Not paid work hours"), 'total': not_paid_hours})

            sql = string.format(overtime, run_ids)
            cr.execute(sql)
            overtime_hours = cr.fetchone()[0]
            result_list.append({'description': _(u"Overtime work hours"), 'total': overtime_hours})

            sql = "SELECT COUNT(DISTINCT(date_start)) FROM hr_payslip_run WHERE id IN {0}".format(run_ids)
            cr.execute(sql)
            number_of_months = cr.fetchone()[0]

            total = done_hours + not_done_hours_company + not_paid_hours + not_done_hours_not_company + overtime_hours

            employee_number = {}
            for run in payslip_runs:
                if not run.salary_in_kind and not run.i3_add_only_inputs and not run.i3_profit_payment:
                    for payslip in run.slip_ids:
                        if payslip.struct_id.code not in ('HR3', 'HR4') and not payslip.annual_calculation:
                            if run.id not in employee_number:
                                employee_number.update({run.id: {'number': 1}})
                            else:
                                employee_number[run.id]['number'] += 1
            total_number = 0
            for el in employee_number:
                total_number += employee_number[el]['number']

            # changed from int to float because int is misleading and report is informative anyway - it is easier to cast manually from float to int if necessary,
            average_employee = total_number/float(number_of_months)
            average_hours = total/average_employee
        result_list.append({'description': _(u'Average number of employees for the year'), 'total': average_employee})
        result_list.append({'description': _(u'Average number of work hours by employee'), 'total': average_hours})
        result_list.insert(0, {'description': _(u'Total'), 'total': total})
        return result_list

    def settlement_of_work(self, date):
        employee = []
        after = self.get_employees(date)['after']
        on_date_emp_ids = [x['employee_id'] for x in after]
        company_lang = self.env.user.company_id.partner_id.lang or 'en_US'
        if on_date_emp_ids:
            employee_sql= f"""
            WITH city_names AS (
                SELECT
                    ct.id AS city_id,
                    ct.name AS city_name_json,
                    COALESCE(
                        ct.name ->> '{company_lang}',
                        ct.name ->> 'en_US',
                        ct.name ->> (SELECT jsonb_object_keys(ct.name) LIMIT 1)
                    ) AS city_name
                FROM
                    res_city ct
            )
            SELECT
                COUNT(DISTINCT employee.id) AS total,
                city_names.city_name AS description,
                COUNT(women.id) AS women
            FROM
                hr_employee employee
            LEFT JOIN
                hr_employee women ON (women.id = employee.id AND women.gender = 'female')
            LEFT JOIN
                res_partner partner ON partner.id = employee.address_work_id
            LEFT JOIN
                city_names ON city_names.city_id = partner.city_id
            WHERE
                employee.id IN ({', '.join(map(str, on_date_emp_ids))})
            GROUP BY
                city_names.city_id, city_names.city_name;
        """
            self._cr.execute(employee_sql)
            employee = self._cr.dictfetchall()
        total = 0
        women = 0
        for el in employee:
            total += el['total']
            women += el['women']
        employee.insert(0, {'description': _(u'Total'), 'total': total, 'women': women})
        return employee

    def return_total(self, result):
        data = {'description': _(u'Total'), 'total': 0, 'women': 0}
        for el in result:
            data['total'] += int(el['total'])
            data['women'] += int(el['women'])
        result.insert(0, data)
        return result

    def return_period(self, date):
        period = date[5:7] + '/' + date[:4]
        return period

    def return_last_date(self, date):
        date_first = date[:-2] + '01'
        date_last_left = (datetime.strptime(
            date_first, '%Y-%m-%d') + relativedelta(months=+1, days=-1)).strftime('%d.%m.%Y')
        return date_last_left

    def return_year_before(self, date):
        year = str(int(date[:4]) - 1)
        return year
