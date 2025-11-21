# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ContributionsRecapReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_contributions_recap'
    _description = 'Contributions recap report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        doc_ids = self.env.context['active_ids']
        doc_model = self.env.context['active_model']
        docs = self.env[doc_model].browse(doc_ids)

        prec = self.env['decimal.precision'].precision_get('Payroll')
        year = self.env['account.fiscal.year'].browse(data.get('year_id'))
        report_data, sum_dict = self.get_data(year)
        report_values = {
            'company': self.env.user.company_id,
            'prec': prec,
            'report_date': data.get('report_date'),
            'data': report_data,
            'sum_dict': sum_dict,
            'employees_by_exp_benefit': self.get_employees_by_exp_benefit(year),
            'year': year,
        }
        return report_values
    
    def get_data(self, year):
        """
        Create a list of dicts, one for each payslip run and one for totals.
        """
        data = []
        sum_dict = {
            'number': 'Ukupno:',
            'month': False,
            'employees_work': False,
            'employees_fee': False,
            'contributions_base': 0,
            'brutto_calc': 0,
            'brutto_paid': 0,
            'emp_exp_12_14': False,
            'emp_exp_12_15': False,
            'emp_exp_12_16': False,
            'emp_exp_12_18': False,
            'emp_exp_total': False
        }
        run_ids = self.get_payslip_run_ids(year)
        for num, run in enumerate(run_ids):
            run_data = self.get_run_name(run)
            emp_data = self.get_employees_data(run)
            amounts_data = self.get_amounts(run)
            line_dict = {
                'number': num + 1,
                'month': run_data,
                'employees_work': emp_data['work'],
                'employees_fee': emp_data['fee'],
                'contributions_base': amounts_data['contributions_base'],
                'brutto_calc': amounts_data['brutto_calc'],
                'brutto_paid': amounts_data['brutto_paid'],
                'emp_exp_12_14': emp_data['1'],
                'emp_exp_12_15': emp_data['2'],
                'emp_exp_12_16': emp_data['3'],
                'emp_exp_12_18': emp_data['4'],
                'emp_exp_total': emp_data['exp_total'],
            }
            # only show payment if base for contributions is > 0, else it doesn't make sense
            if amounts_data['contributions_base'] or amounts_data['brutto_calc'] or amounts_data['brutto_paid']:
                data.append(line_dict)
                sum_dict['contributions_base'] += amounts_data['contributions_base']
                sum_dict['brutto_calc'] += amounts_data['brutto_calc']
                sum_dict['brutto_paid'] += amounts_data['brutto_paid']
        return data, sum_dict

    def get_payslip_run_ids(self, year):
        """
        Return all payslip runs except profit payment and only inputs, sorted by date ASC.
        """
        run_obj = self.env['hr.payslip.run']
        domain = [
            ('date_start', '>=', year.date_from),
            ('date_end', '<=', year.date_to),
            ('i3_profit_payment', '=', False),
            ('i3_add_only_inputs', '=', False)
        ]
        run_ids = run_obj.search(domain, order='date_start ASC')
        return run_ids

    def get_employees_data(self, run):
        """
        Employee can have multiple payslips on same payslip run so we browse through employees and not payslips.
        """
        slip_obj = self.env['hr.payslip']
        emp_ids = self.get_run_employee_ids(run)
        res = {
            'work': 0,
            'fee': 0,
            # keys are same as selection field on contract for simpler addition
            # 1 - 12 / 14
            # 2 - 12 / 15
            # 3 - 12 / 16
            # 4 - 12 / 18
            '1': 0,
            '2': 0,
            '3': 0,
            '4': 0,
            'exp_total': 0,
        }
        for emp_id in emp_ids:
            emp_slips = slip_obj.search([('payslip_run_id', '=', run.id), ('employee_id', '=', emp_id)])
            emp_data = self.get_payslip_employee_data(emp_slips)
            if emp_data['has_worked']:
                res['work'] += 1
            else:
                res['fee'] += 1
            if emp_data['benefit'] != '0':
                res['exp_total'] += 1
                res[emp_data['benefit']] += 1
        return res
    
    def get_run_employee_ids(self, run):
        sql = """
            SELECT DISTINCT(e.id)
            FROM hr_payslip AS s
            JOIN hr_employee AS e ON (s.employee_id = e.id)
            WHERE s.payslip_run_id = {0}
        """.format(run.id)
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        return [emp_dict['id'] for emp_dict in res]
    
    def get_payslip_employee_data(self, slips):
        """
        Return if employee worked the month and work exp benefit level for the month.
        """
        slip_obj = self.env['hr.payslip']
        fond_list = self.env['hr.payroll.salary.rule.configuration'].get_rules('bolovanje_fond')
        benefit = False
        has_worked = True
        work_hours = fee_hours = 0
        for slip in slips:
            # if employee has multiple payslips with different contracts on payslip_run, contract from last one will be taken
            # since we can only show one piece of info for each employee on payslip_run,
            # info will always be wrong if benefit_types on contracts are not the same and correct if they are, so it doesn't matter which one we take
            benefit = slip.salary_parameters_id.internship_type
            # we count employee as having worked the month if they spent more (or same) hours at work than not working and receiving HZZO fee
            for wd in slip.worked_days_line_ids:
                if wd.code in fond_list:
                    fee_hours += wd.number_of_hours
                else:
                    work_hours += wd.number_of_hours
        if fee_hours > work_hours:
            has_worked = False
        return {
            'has_worked': has_worked,
            'benefit': benefit,
        }
    
    def get_amounts(self, run):
        # OSNDOP je osnovica za doprinose, bez obzira da li radnik stvarno prima placu ili je na izaslanom radu, strucnom ili izostaje
        # tu osnovicu je potrebno razdijeliti na one koji primaju placu i koji ne primaju placu
        # stoga zbrajamo izostanak, izaslani rad i strucno te na kraju oduzimamo od ukupne osnovice
        # za svaku isplatu se gleda samo je li isplacena ili neisplacena ('nonpaid_salary') u trenutku ispisa izvjestaja
        base = calc = paid = 0
        sql = """
            SELECT line.code AS pl_code, line.total AS pl_total, str.code AS struct_code
            FROM hr_payslip_line AS line
            JOIN hr_payslip AS slip ON slip.id = line.slip_id
            JOIN hr_payroll_structure AS str ON str.id = slip.struct_id
            WHERE slip.payslip_run_id = {0}
            AND line.code IN ('OSNDOP','IZS')
        """.format(run.id)
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        for line in res:
            izaslani = (line['pl_code'] == 'IZS')
            strucno = (line['struct_code'] in ('HR3','HR4'))
            izostanak_radnika = (line['struct_code'] == 'HR13')
            if izaslani or strucno or izostanak_radnika:
                base += line['pl_total']
                calc -= line['pl_total']
                paid -= line['pl_total']
            if line['pl_code'] == 'OSNDOP':
                calc += line['pl_total']
                if run.payslip_run_type != 'nonpaid_salary':
                    paid += line['pl_total']
        return {
            'contributions_base': base,
            'brutto_calc': calc,
            'brutto_paid': paid,
        }

    def get_run_name(self, run):
        # za bozicnicu, regres uskrsnicu i slicno treba ispisati vrstu isplate (prikazuje se na izvjestaju samo ako je oporeziva isplata), inace mjesec
        if run.i3_add_only_inputs:
            return run.name
        return str(run.date_start.month)

    def get_benefit_mapping(self):
        """
        Get values from selection field because they contain the exact benefit level (12/14, 12/15 etc).
        For gathering data we use the ids ('0', '1', '2' etc) because it is simpler, but for the report we need actual level values.
        """
        benefit_types = self.env['hr.salary.parameters']._fields['internship_type']._description_selection(self.env) # list of tuples
        benefit_mapping = {}
        for line in benefit_types:
            benefit_mapping.update({line[0]: line[1].split(' - ')[1]}) # levels look like '1 - 12/14' -> we only want the 12/14
        return benefit_mapping
    
    def get_employees_by_exp_benefit(self, year):
        benefit_mapping = self.get_benefit_mapping()
        data = self.get_exp_benefit_employees_data(year)
        report_data = self.group_exp_benefit_data(year, data, benefit_mapping)
        return report_data

    def get_exp_benefit_employees_data(self, year):
        # join from payslip_run to be in sync with first part of the report
        # limit contract dates with current year immediately so there is no need to adjust later
        sql = """
            SELECT emp.id AS emp_id, emp.name AS emp_name, emp.hzmo_id AS emp_osobni_broj,
            emp.oib AS oib, job.name AS emp_job, params.internship_type AS benefit, 
            (CASE WHEN params.date_from < '{0}' THEN '{0}' ELSE params.date_from END) AS params_start, 
            (CASE WHEN (params.date_to >= '{1}' OR params.date_to IS NULL) THEN '{1}' ELSE params.date_to END) AS params_end
            FROM hr_payslip_run AS run
            JOIN hr_payslip AS slip ON (slip.payslip_run_id = run.id)
            JOIN hr_salary_parameters AS params ON (slip.salary_parameters_id = params.id)
            JOIN hr_employee AS emp ON (slip.employee_id = emp.id)
            JOIN hr_job AS job ON (params.job_id = job.id)
            WHERE run.date_start >= '{0}'
            AND run.date_end <= '{1}'
            AND params.internship_type != '0'
            GROUP BY params.internship_type, params.date_from, params.date_to, emp.job_id, emp.name, emp.id, job.id, emp.hzmo_id, emp.oib
            ORDER BY params.internship_type, emp.name, params.date_from
        """.format(year.date_from, year.date_to)
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        return data

    def group_exp_benefit_data(self, year, data, benefit_mapping):
        # input data: sorted by benefit level, employee name and contract start date
        # we want to create a list of dicts, one for each level of benefit (that is actually in use)
        # each dict contains 'year' and 'benefit' for report title and 'data' list
        # data contains one line for each (employee, benefit) combo
        # benefit mapping is used to get actual levels values instead of their ids ('1' is used for gathering data but we actually need 12/14 so we do this here)
        res = []
        emp_line = {}
        res_index = -1
        num = 0
        for index, line in enumerate(data):
            line['benefit'] = benefit_mapping[line['benefit']]
            line['emp_job'] = line['emp_job'][self.env.user.partner_id.lang]
            # new benefit level -> new list element
            if not res or (emp_line and emp_line['benefit'] != line['benefit']):
                res_index += 1
                res.append({
                    'level': line['benefit'],
                    'year': year.name,
                    'data': []
                })
            # same (employee, benefit) combo -> extend period for current employee and continue
            if emp_line and line['emp_id'] == emp_line['emp_id'] and line['benefit'] == emp_line['benefit']:
                emp_line['params_end'] = line['params_end']
            # either employee or benefit is different -> append current employee line and update it for further use
            else:
                # in first iteration there is no current employee line so we just set it and continue
                if index > 0:
                    num += 1
                    emp_line.update({'number': num})
                    # if benefit is changed then res_index has already been increased and we need to append to previous level, else we are at the correct level
                    if emp_line['benefit'] != line['benefit']:
                        res[res_index - 1]['data'].append(emp_line)
                        num = 0
                    else:
                        res[res_index]['data'].append(emp_line)
                emp_line = line
                
        # last employee line is never appended inside for loop so we do it here
        # we have nothing to append if there is no data
        if emp_line:
            emp_line.update({'number': num + 1})
            res[res_index]['data'].append(emp_line)
        return res
