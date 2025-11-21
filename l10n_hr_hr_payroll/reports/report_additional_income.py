# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from ..models import payroll_common as paycom

class AdditionalIncomeReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_additional_income'
    _description = 'Additional income report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        obj_name = 'hr.employee'
        emp_obj = self.env[obj_name]
        year_id = data['year_id']
        print_date = data['print_date']
        emp_ids = data['employee_ids']
        year = self.env['account.fiscal.year'].browse(year_id)
        add_income_data = self.get_additional_income_data(year, emp_ids)
        emp_lines = self.group_data_by_employee(add_income_data)
        emp_data = {}
        emps = []
        for key in emp_lines:
            emp = emp_obj.browse(key)
            emp_data.update({
                key: {
                    'name': emp._get_display_name_format('first_name_first').format(emp.first_name, emp.last_name),
                    'address': self.get_employee_address(emp),
                    'oib': emp.oib,
                    'slip_lines': emp_lines[key],
                }
            })
            emps.append(emp)
        company = self.env.user.company_id
        return {
            'doc_ids': emp_ids,
            'doc_model': obj_name,
            'docs': emps,
            'data': emp_data,
            'year': year,
            'print_date': print_date,
            'company': company,
            'company_address': self.get_company_address(company),
        }
    
    def get_additional_income_data(self, year, emp_ids):
        """
        Get data from additional income payslips for all employees in given year.
        """
        date_from = year.date_from
        date_to = year.date_to
        struct_codes = paycom.get_structures()['additional_income']
        payroll_conf = self.env['hr.payroll.salary.rule.configuration']
        doprinosi = payroll_conf.get_rules('doprinosi_iz_place')
        priznati_izdatak = payroll_conf.get_rules('priznati_izdatak')
        emps_cond = paycom.get_ids_sql_condition(emp_ids)
        params = {
            'date_from': date_from,
            'date_to': date_to,
            'struct_codes': struct_codes,
            'doprinosi': doprinosi,
            'priznati_izdatak': priznati_izdatak,
        }
        query = """
            SELECT slip.employee_id AS emp_id,
            slip.paid_date AS date_paid,
            COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'BASIC' AND slip.id = slip_id), 0) AS primitak,
            COALESCE( (SELECT SUM(rate) FROM hr_payslip_line WHERE code IN %(priznati_izdatak)s AND slip.id = slip_id), 0) AS izdatak_pct,
            COALESCE( (SELECT SUM(total) FROM hr_payslip_line WHERE code IN %(priznati_izdatak)s AND slip.id = slip_id), 0) AS izdatak,
            COALESCE( (SELECT SUM(total) FROM hr_payslip_line WHERE code IN %(doprinosi)s AND slip.id = slip_id), 0) AS doprinosi,
            COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'DOH' AND slip.id = slip_id), 0) AS dohodak,
            COALESCE( (SELECT SUM(total) FROM hr_payslip_line WHERE code IN ('PDOH') AND slip.id = slip_id), 0) AS porez,
            COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'ISPL' AND slip.id = slip_id), 0) AS isplata,
            b62.name AS oznaka_primitka
            FROM hr_payslip AS slip
            LEFT JOIN hr_payroll_structure AS struct ON struct.id = slip.struct_id
            LEFT JOIN hr_employee AS emp ON emp.id = slip.employee_id
            LEFT JOIN hr_salary_parameters AS params ON params.id = slip.salary_parameters_id
            LEFT JOIN l10n_hr_joppd_sifre AS b62 ON b62.id = params.joppd_b62
            WHERE slip.paid_date >= '{0}'
            AND slip.paid_date <= '{1}'
            AND struct.code IN %(struct_codes)s
            AND emp.id IN {2}
            ORDER BY slip.employee_id, slip.paid_date, slip.date_from
        """.format(date_from, date_to, emps_cond)
        self.env.cr.execute(query, params)
        data = self.env.cr.dictfetchall()
        return data

    def group_data_by_employee(self, add_income_data):
        emp_data = {}
        for slip_line in add_income_data:
            key = slip_line['emp_id']
            if key not in emp_data:
                emp_data[key] = []
            emp_data[key].append(slip_line)
        return emp_data

    def get_company_address(self, company):
        city = company.city_id.name
        if not company.street:
            return city
        return city + ', ' + company.street

    def get_employee_address(self, emp):
        city = emp.city.name
        if not emp.street:
            return city
        return city + ', ' + emp.street
    