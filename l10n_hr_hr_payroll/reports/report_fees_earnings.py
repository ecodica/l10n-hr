from odoo import api, models, _

class ReportFeesEarningsParser(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_fees_earnings'
    _description = 'Employee fees and earnings report parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        payslip_runs = self.env['hr.payslip.run'].search([('id', 'in', data['run_ids'])])
        company = payslip_runs[0].company_id
        if data['department_id']:
            department = [self.env['hr.department'].search([('id', '=', data['department_id'])]).id]
        else:
            department = str(self.env['hr.department'].search([]).ids)
        
        # TODO ne hardkodirat report_type
        report_type = data['type']

        employees_data, sums = self.get_payslip_lines(payslip_runs, report_type, department)

        company_data = self.get_company_data(company)

        docargs = {
            'payslip': payslip_runs,
            'company': company_data,
            'data': employees_data,
            'sums': sums,
            'lang': self.get_company_language(),
            'title': self.get_title(report_type)
        }
        return docargs

    def get_company_language(self):
        return self.env.user.company_id.partner_id.lang

    def get_payslip_lines(self, payslip_runs, report_type, departments):
        lang =self.get_company_language()
        codes = ""
        payslip_cond = self.get_conds(payslip_runs.ids)
        payroll_conf = self.env['hr.payroll.salary.rule.configuration']
        fees_codes = payroll_conf.get_rules('fees')
        earnings_codes = payroll_conf.get_rules('earnings')
        sick_leave_fund_codes = payroll_conf.get_rules('bolovanje_fond')
        sick_leave_fund_without_injury_at_work_codes = payroll_conf.get_rules('sick_leave_fund_without_injury_at_work')
        sick_leave_company_without_injury_at_work_codes = payroll_conf.get_rules('sick_leave_company_without_injury_at_work')
        injury_at_work_codes = payroll_conf.get_rules('injury_at_work')
        if report_type == 'fees':
            codes = fees_codes + sick_leave_fund_codes
        elif report_type == 'earnings':
            codes = earnings_codes
        elif report_type == 'sick_leave_company':
            codes = sick_leave_company_without_injury_at_work_codes
        elif report_type == 'sick_leave_fund':
            codes = sick_leave_fund_without_injury_at_work_codes
        elif report_type  == 'injury_at_work':
            codes = injury_at_work_codes
        cond = self.get_conds(departments)
        params = {
            'codes': codes,
        }
        query = """
            SELECT  em.code,
                    em.name,
                    hpl.name,
                    SUM(wd.number_of_hours),
                    SUM(hpl.total),
                    hpl.code,
                    c.skip_hours,
                    em.id
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            LEFT JOIN hr_payslip_worked_days AS wd ON (hp.id = wd.payslip_id AND hpl.code = wd.code)
            LEFT JOIN hr_salary_rule_category AS c ON (c.id = hpl.category_id)
            WHERE hpl.code IN %(codes)s AND hpr.id {0}
            AND hp.department_id {1}
            GROUP BY em.code, em.name, hpl.code, em.id, hpl.sequence, hpl.name, c.skip_hours
            ORDER BY em.name, hpl.sequence
            """.format(payslip_cond, cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall() 

        employees_data = {}
        sums = {}
        for emp_data in res:
            # group by ID
            key = emp_data[7]
            if key not in employees_data:
                employees_data[key] = {}
                employees_data[key]['line'] = []
                employees_data[key]['name'] = emp_data[1]
                employees_data[key]['total_hours'] = 0
                employees_data[key]['total_amount'] = 0
            employees_data[key]['line'].append(emp_data)
            if emp_data[2] not in sums:
                sums[emp_data[2]] = {"hours": 0, "amount": 0}
            employees_data[key]['total_hours'] += emp_data[3] or 0
            employees_data[key]['total_amount'] += emp_data[4] or 0
            sums[emp_data[2]]['hours'] += emp_data[3] or 0
            sums[emp_data[2]]['amount'] += emp_data[4] or 0
        return employees_data, sums


    def get_conds(self, department_ids):
        cond = "IN " + str(department_ids)
    
        cond = cond.replace("[", "(")
        cond = cond.replace("]", ")")
    
        return cond
    
    def get_company_data(self, company):
        company_data = {}
        company_data['name'] = company.partner_id.name
        company_data['address'] = str(company.street) + ', ' + str(company.zip) + ', ' + str(company.city_id.name) +', ' + str(company.country_id.name)
        company_data['oib'] = company.company_registry
        company_data['currency'] = company.currency_id
        return company_data

    def get_title(self, report_type):
        if report_type == 'fees':
            return 'Popis naknada'
        elif report_type == 'earnings':
            return 'Popis zarada'
        elif report_type == 'sick_leave_company':
            return 'Bolovanje na teret poslodavca'
        elif report_type == 'sick_leave_fund':
            return 'Bolovanje na teret HZZO-a'
        elif report_type == 'injury_at_work':
            return 'Ozljede na radu'
        else:
            return False
