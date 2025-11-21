from odoo import api, models, _

class PayrollConfirmationReportParser(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_tax_city'
    _description = 'Tax city report parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        payslip_runs = self.env['hr.payslip.run'].search([('id', 'in', data['run_ids'])])
        company = payslip_runs[0].company_id
        if data['department_id']:
            department = [self.env['hr.department'].search([('id', '=', data['department_id'])]).id]
        else:
            department = str(self.env['hr.department'].search([]).ids)

        cities_data = self.group_data(self.get_lines(payslip_runs, department))
        payslips_sums = self.get_lines_sum(payslip_runs, department)
        company_data = self.get_company_data(company)

        docargs = {
            'payslip_runs': payslip_runs,
            'cities_data': cities_data,
            'sums': payslips_sums,
            'name': data['name'],
            'company': company_data
        }
        return docargs

    def get_company_data(self, company):
        company_data = {}
        company_data['name'] = company.partner_id.name
        company_data['address'] = str(company.street) + ', ' + str(company.zip) + ', ' + str(company.city_id.name) +', ' + str(company.country_id.name)
        company_data['oib'] = company.company_registry
        company_data['currency'] = company.currency_id
        return company_data

    def group_data(self, data):
        data_by_city = {}
        for city_data in data:
            if(city_data[0] not in data_by_city):
                data_by_city[city_data[0]] = {}
                data_by_city[city_data[0]]['total'] = ""
                data_by_city[city_data[0]]['line'] = []

            if city_data[7] == 'state':
                continue
            elif city_data[7] == 'total':
                data_by_city[city_data[0]]['total'] = city_data
            else:
                data_by_city[city_data[0]]['line'].append(city_data)

        return data_by_city

    def get_lines(self, obj, department_ids):
        conds = self.get_conds(department_ids)
        run_id = self.get_conds(obj.ids)
        porez = self.env['hr.payroll.salary.rule.configuration'].get_rules('rekapitulacija_poreza')
        params = {
            'porez': porez,
        }

        self.env.cr.execute("""
                            SELECT city.id as city_id,  pl.code, sum(pl.total) as total, em.name as em_name,em.id as em_id, em.oib
                            FROM hr_payslip AS ps
                            JOIN hr_payslip_run as pr ON (ps.payslip_run_id = pr.id)
                            JOIN hr_payslip_line AS pl ON (ps.id = pl.slip_id) AND pl.code IN %(porez)s
                            JOIN hr_employee AS em ON (pl.employee_id = em.id)
                            LEFT OUTER JOIN hr_department AS dep ON (dep.id = ps.department_id)
                            JOIN res_company AS co ON (dep.company_id = co.id)
                            LEFT OUTER JOIN res_partner AS cpar ON (co.partner_id = cpar.id)
                            LEFT OUTER JOIN res_city AS city ON (city.id = em.city)
                            WHERE ps.department_id {0} AND pr.id {1}
                            GROUP BY city.id, pl.code, em.name, em_id, em.oib
                            ORDER BY city.id """.format(conds, run_id), params)

        res = self.env.cr.dictfetchall()
        lines = {}
        city_ids = self.env['res.city'].search([])
        city_names = {city.id: city.name for city in city_ids}
        employees ={}
        # get totals for each state
        for line in res:
            city_id = line['city_id']
            emp_id = line['em_id']
            if city_id not in lines:
                lines[city_id] = {}
            if emp_id not in employees:
                employees[emp_id] = line['em_name']
            if emp_id in lines[city_id]:
                lines[city_id] = {}
                if line['code'] == "PDOH":
                    lines[city_id][emp_id].update({'PDOH': line['total']})
                else:
                    lines[city_id][emp_id].update({'PRIR': line['total']})
            else:
                if line['code'] == "PDOH":
                    lines[city_id][emp_id] = {
                        'PRIR': 0,
                        'PDOH': line['total'],
                        'total': line['total'],
                        'identification_id': line['oib']
                    }
                else:
                    lines[city_id][emp_id] = {
                        'PRIR': line['total'],
                        'PDOH': 0,
                        'total': line['total'],
                        'identification_id': line['oib']
                    }
        # group employee lines by state
        list = []
        for key in lines:
            list.append([city_names[key], '', '', 0, 0, 0, '', 'state'])
            for emp in lines[key]:
                line_type = 'line'
                emp_vat = lines[key][emp]['identification_id']
                emp_pdoh = lines[key][emp]['PDOH']
                emp_prir = lines[key][emp]['PRIR']
                emp_total = emp_pdoh + emp_prir
                list.append([city_names[key], employees[emp], emp_vat, emp_pdoh, emp_prir, emp_total, '', line_type])

        result = sorted(list, key=lambda k: (k[0], k[1], k[6]))

        # get state totals
        if result:
            state_key = result[0][0]
        else:
            state_key = ""
        state_pdoh = 0
        state_prir = 0
        state_total = 0
        final_list = []
        line_type = 'total'
        rbr = 1
        for r in result:
            if state_key != r[0]:
                rbr = 1
                final_list.append([state_key, _('Total'), '', state_pdoh, state_prir, state_total, '', line_type])
                state_pdoh = r[3]
                state_prir = r[4]
                state_total = r[5]
                state_key = r[0]
            else:
                state_pdoh += r[3]
                state_prir += r[4]
                state_total += r[5]
                
            if r[7] == 'line':
                r[6] = rbr
                rbr += 1

            final_list.append(r)

            if r == result[-1]:
                final_list.append([state_key, _('Total'), '', state_pdoh, state_prir, state_total, '', line_type])

        return final_list

    def get_lines_sum(self, obj, department_ids):
        conds = self.get_conds(department_ids)
        run_id = self.get_conds(obj.ids)
        porez = self.env['hr.payroll.salary.rule.configuration'].get_rules('rekapitulacija_poreza')
        params = {
            'porez': porez,
        }
        self.env.cr.execute("""SELECT  city.name, pl.code, sum(pl.total) as total
                           FROM hr_payslip AS ps 
                           JOIN hr_payslip_run as pr ON (ps.payslip_run_id = pr.id)
                           JOIN hr_payslip_line AS pl ON (ps.id = pl.slip_id) AND pl.code IN %(porez)s
                           JOIN hr_employee AS em ON (pl.employee_id = em.id)
                           LEFT OUTER JOIN hr_department AS dep ON (dep.id = ps.department_id)
                           JOIN res_company AS co ON (dep.company_id = co.id)
                           LEFT OUTER JOIN res_partner AS cpar ON (co.partner_id = cpar.id)
                           LEFT OUTER JOIN res_city AS city ON (city.id = em.city)
                           WHERE ps.department_id {0} AND pr.id {1}
                           GROUP BY city.name, pl.code, cpar.vat
                           ORDER BY city.name """.format(conds, run_id), params)
        
        res = self.env.cr.dictfetchall()
        total = 0
        pdoh = 0
        prir = 0
        for line in res:
            if line['code'] == "PDOH":
                pdoh += line['total']
            else:
                prir += line['total']
            total += line['total']

        return [(round(pdoh, 2), round(prir, 2), round(total, 2))]

    def get_conds(self, department_ids):
        cond = "IN " + str(department_ids)
       
        cond = cond.replace("[", "(")
        cond = cond.replace("]", ")")
        
        return cond
