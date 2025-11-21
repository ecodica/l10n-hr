# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from ..models import payroll_common as paycom

class HrPayslipRunRecapReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_hr_payslip_run_recap'
    _description = 'Payslip run recap report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        doc_ids = self.env.context['active_ids']
        doc_model = self.env.context['active_model']
        docs = self.env[doc_model].browse(doc_ids)
        run_ids = data['run_ids']
        run_obj = self.env['hr.payslip.run']
        runs = run_obj.browse(run_ids)
        dep_id = data['department_id']
        department_ids = data['department_ids']
        dep_cond = self.get_department_condition(department_ids)
        run_cond = self.get_payslip_run_condition(run_ids)
        report_data = {
            'company': self.env.user.company_id,
            'department_name': self.env['hr.department'].browse(dep_id).name,
            'number_of_employees': self.get_employees(run_cond, dep_id, department_ids),
            'run_names': self.get_payslip_run_names(runs),
            'payslip_totals': self.get_payslip_totals(runs, dep_cond),
            'contributions_from_salaries': self.get_contributions_from_salaries(run_cond, dep_cond),
            'work_abroad_hr': self.get_work_abroad_hr(run_cond, dep_cond),
            'income': self.get_income(run_cond, dep_cond),
            'admitted_cost': self.get_admitted_cost(run_cond, dep_cond),
            'taxes': self.get_taxes(run_cond, dep_cond),
            'neto': self.get_neto(run_cond, dep_cond),
            'work_abroad_ino': self.get_work_abroad_ino(run_cond, dep_cond),
            'payslip_lines_totals': self.get_payslip_compensations(run_ids, dep_cond),
            'suspensions': self.get_suspensions(run_cond, dep_cond),
            'payment': self.get_payment(run_cond, dep_cond),
            'contributions_on_salaries': self.get_contributions_on_salaries(run_cond, dep_cond),
            'brutto2': self.get_brutto2(run_cond, dep_cond),
            'local_tax': self.get_local_tax_totals(run_cond, dep_cond),
            'local_tax_sum': self.get_sum_local_tax(run_cond, dep_cond),
            'lang':self.get_company_language(),
        }
        return {
            'doc_ids': doc_ids,
            'doc_model': doc_model,
            'docs': docs,
            'data': report_data,
        }

    def get_company_language(self):
        return self.env.user.company_id.partner_id.lang

    def get_payslip_run_names(self, runs):
        run_names = ''
        for run in runs:
            run_names += run.name + ', '
        return run_names[:-2]

    def get_payslip_run_condition(self, run_ids):
        if len(tuple(set(run_ids))) == 1:
            cond = "= " + str(run_ids[0])
        else:
            cond = "IN " + str(tuple(set(run_ids)))
        return cond

    def get_department_condition(self, department_ids):
        if len(tuple(set(department_ids))) == 1:
            cond = "= " + str(department_ids[0])
        else:
            cond = "IN " + str(tuple(set(department_ids)))
        return cond
    
    def get_employees(self, run_cond, dep_id, department_ids):
        cond = "AND depart.id IN ({})".format(','.join([str(d_id) for d_id in department_ids])) if dep_id else ""
        query = """
            SELECT count(DISTINCT pl.employee_id)
            FROM hr_payslip_run as run
            LEFT JOIN hr_payslip as pl ON(run.id = pl.payslip_run_id)
            LEFT JOIN hr_department as depart ON(pl.department_id = depart.id)
            WHERE run.id {0} {1}
        """.format(run_cond, cond)
        self.env.cr.execute(query)
        res = self.env.cr.fetchone()
        return res[0]
    
    def get_payslip_totals(self, runs, department_cond):
        payslip_run_ids = runs.ids
        payslip_ids = self.env['hr.payslip'].search([('payslip_run_id', 'in', payslip_run_ids)])
        payslip_ids = tuple(payslip_ids.ids)
        
        if len(payslip_ids) == 0:
            raise ValidationError('Odabrani obracun nema nijedan zapis!')
        elif len(payslip_ids) == 1:
            payslip_cond = "= " + str(payslip_ids[0]) 
        else:
            payslip_cond = "IN " + str(tuple(payslip_ids))
        
        bolovanje_na_fond = self.env['hr.payroll.salary.rule.configuration'].get_rules('bolovanje_fond')
        bruto_dodaci_kategorije = self.env['hr.payroll.salary.rule.category.configuration'].get_category('bruto_dodaci')
        params={
            'payslip_cond': payslip_cond,
            'department_cond': department_cond,
            'bolovanje_na_fond': bolovanje_na_fond,
            'bruto_dodaci_kategorije': bruto_dodaci_kategorije,
        }
        query_1 = """
            SELECT pl.name, SUM(number_of_hours),
            SUM(pl.amount),pl.code, c.skip_hours
            FROM hr_payslip_worked_days AS wd 
            LEFT JOIN hr_payslip_line AS pl ON(wd.payslip_id = pl.slip_id) 
            LEFT JOIN hr_payslip AS ps ON(pl.slip_id = ps.id)
            LEFT JOIN hr_department AS hd ON(ps.department_id = hd.id)
            LEFT JOIN hr_salary_rule_category AS c ON (c.id = pl.category_id)
            WHERE wd.code = pl.code 
            AND wd.payslip_id {0} AND hd.id {1} AND pl.code not in %(bolovanje_na_fond)s
            GROUP BY pl.code,pl.name,c.skip_hours
        """.format(payslip_cond, department_cond)
        self.env.cr.execute(query_1, params)
        res = self.env.cr.fetchall()

        query_2 = """
            SELECT pl.name,0, 
            SUM(pl.total),pl.code, rc.skip_hours
            FROM hr_payslip_line AS pl                      
            LEFT JOIN hr_payslip AS ps ON(pl.slip_id = ps.id)
            LEFT JOIN hr_department AS hd ON(ps.department_id = hd.id)
            LEFT JOIN hr_salary_rule_category AS rc ON (rc.id = pl.category_id) 
            WHERE (rc.code IN %(bruto_dodaci_kategorije)s)
            AND ps.id {0} AND hd.id {1}
            GROUP BY pl.code,pl.name, rc.skip_hours
        """.format(payslip_cond, department_cond)
        self.env.cr.execute(query_2, params)
        res.extend(self.env.cr.fetchall())
        total_hours = 0
        total_brutto = 0
        for index,el in enumerate(res):
            el = list(el)
            el.append('line')
            el = tuple(el)
            res[index] = el 
            total_hours += 0 if el[4] else el[1]
            total_brutto += el[2]
        # total work hours do not include categories with skip_hours (check other reports as well)
        res.append(('Ukupno', total_hours, total_brutto, '', '','total'))
        return res

    def get_local_tax_totals(self, run_cond, dep_cond):
        # added COALESCE to hp.local_tax for annual calculation payslips - they are not created the usual way so some fields are null
        # this also means tax returns are shown separate from tax payment to cities (since payment only exists if local_tax > 0) even though they cancel each other
        # it should not be a problem, in fact it might be clearer this way
        query = """
            SELECT city.id, SUM(hpl.total)
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_salary_parameters AS params ON (params.id = hp.salary_parameters_id)
            LEFT JOIN hr_department AS hd ON (params.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)	                       
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            LEFT JOIN res_city AS city ON (city.id = em.city)
            WHERE hpl.total <> 0 AND hpl.code LIKE 'PDOH' AND hpr.id {0} AND hd.id {1}
            GROUP BY city.id
            ORDER BY city.id
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        city_ids = self.env['res.city'].search([])
        city_names = {city.id: city.name for city in city_ids}
        lines = {}
        lines_with_city_names = []
        for row in res:
            city_id = row[0]
            value = row[1]
            lines[city_id] = value
        for city_id, value in lines.items():
            city_name = city_names.get(city_id, 'Unknown City')
            lines_with_city_names.append({
                'city_name': city_name,
                'amount': value
            })
        return lines_with_city_names

    def get_brutto2(self, run_cond, dep_cond):
        """
        Sums all payslip lines with bruto2 categories on given payslip_run, except if payslip has structure with contributions only -> then only sum contributions.
        """
        query_data = self.env['hr.hr.payroll.reports.common'].get_brutto2_query_data()
        query = """
            SELECT SUM(hpl.total)
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payroll_structure AS hss ON (hss.id = hp.struct_id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            LEFT JOIN res_partner ON (em.address_home_id = res_partner.id)
            LEFT JOIN res_country_state AS rcs ON (res_partner.state_id = rcs.id)
            WHERE hpr.id {1} AND hd.id {2} AND (
                -- standardni slucaj
                (hss.id NOT IN {6} AND hpl.code IN {0}) OR
                -- isplata doprinosa
                (hss.id IN {3} AND hpl.code IN {4}) OR
                -- izaslani rad s porezom u inozemstvu 
                -- racunamo sve osim BASIC jer se na tu osnovicu samo placaju doprinosi, a placa se obracunava po ino satnici
                (hss.id IN {5} AND hpl.code IN {7})
            )
        """.format(
            query_data['brutto_2'],
            run_cond,
            dep_cond,
            query_data['structures_with_contributions_only_ids'],
            query_data['doprinosi'],
            query_data['work_abroad_ino_tax_struct'],
            query_data['exception_struct_ids'],
            query_data['work_abroad_ino_tax_rules'],
        )
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        return res
        
    def get_sum_local_tax(self, run_cond, dep_cond):
        query = """
            SELECT SUM(hpl.total)
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_salary_parameters AS params ON (params.id = hp.salary_parameters_id)	    
            LEFT JOIN hr_department AS hd ON (params.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code LIKE 'PDOH' 
            AND hpr.id {0}
            AND hd.id {1} 
            GROUP BY hpl.code
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        return res

    def get_payslip_compensations(self, run_ids, dep_cond):
        payslip_run_ids = run_ids
        payslip_ids = self.env['hr.payslip'].search([('payslip_run_id', 'in', run_ids)])
        payslip_ids = tuple(payslip_ids.ids)
        payroll_conf = self.env['hr.payroll.salary.rule.configuration'] 
        bolovanje_fond = payroll_conf.get_rules('bolovanje_fond') 
        dodaci_neto = payroll_conf.get_rules('dodaci_neto') 

        if len(payslip_ids) == 0:
            raise ValidationError('Odabrani obracun nema nijedan zapis!')
        
        elif len(payslip_ids) == 1:
            payslip_condition = "= " + str(payslip_ids[0]) 
        else:
            payslip_condition = "IN " + str(tuple(payslip_ids))
        params = {
            'payslip_condition': payslip_condition,
            'bolovanje_fond': bolovanje_fond,
        }
        query_1 = """
            SELECT pl.name, SUM(number_of_hours), 
            SUM(pl.amount),pl.code 
            FROM hr_payslip_worked_days as wd 
            LEFT JOIN hr_payslip_line as pl ON(wd.payslip_id = pl.slip_id) 
            LEFT JOIN hr_payslip as ps ON(pl.slip_id = ps.id) 
            LEFT JOIN hr_department as hd ON(ps.department_id = hd.id)
            WHERE wd.code = pl.code 
            --AND pl.amount <> 0 
            AND wd.payslip_id 
            {0} AND hd.id  {1} 
            AND pl.code in %(bolovanje_fond)s GROUP BY pl.code,pl.name
        """.format(payslip_condition, dep_cond)
        self.env.cr.execute(query_1, params)
        res = self.env.cr.fetchall()

        query_2 = """
            SELECT pl.name,0, 
            SUM(pl.total),pl.code
            FROM hr_payslip_line as pl                         
            LEFT JOIN hr_payslip as ps ON(pl.slip_id = ps.id) 
            LEFT JOIN hr_department as hd ON(ps.department_id = hd.id)
            WHERE (pl.code in {0})
            AND ps.id {1} AND hd.id {2} GROUP BY pl.code,pl.name
        """.format(dodaci_neto, payslip_condition, dep_cond)
        self.env.cr.execute(query_2)
        res.extend(self.env.cr.fetchall())
        #total = self.get_totals(res)
        total_hours = 0
        total_amount = 0
        for index,el in enumerate(res):
            el = list(el)
            el.append('line')
            el = tuple(el)
            res[index] = el 
            total_hours += el[1]
            total_amount += el[2]
        res.append(('Ukupno nadoknade', total_hours, total_amount, '', 'total'))

        return res
        
    def get_contributions_from_salaries(self, run_cond, dep_cond):
        doprinosi_iz_place = self.env['hr.payroll.salary.rule.configuration'].get_rules('doprinosi_iz_place')
        params={
            'doprinosi_iz_place': doprinosi_iz_place,
        }
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code IN %(doprinosi_iz_place)s AND hpr.id {0} AND hd.id {1} 
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall()
        #dmio total is not equal to sum of dmio1 and dmio2, difference probably in payslip
        dmio = 0
        for position,line in enumerate(res):
            if line[3] in ('DMIO1','DMIO2'):
                dmio += line[2]
            if line[3] == 'DMIO':
                line = (line[0], line[1], dmio, line[3])
                res[position] = line

        total = self.get_totals(res)
        res.append((u'Ukupno doprinosi iz plaće', '', total, '', 'total'))
        return res

    def get_contributions_on_salaries(self, run_cond, dep_cond):
        doprinosi_na_placu = self.env['hr.payroll.salary.rule.configuration'].get_rules('doprinosi_na_placu')
        additional_income_structures = paycom.get_structures()['additional_income']
        params={
            'doprinosi_na_placu': doprinosi_na_placu,
            'additional_income_structures': additional_income_structures,
        }
        query = """
            SELECT DISTINCT(hpl.name),
            CASE WHEN hpl.code = 'DZDR'
            THEN (
                CASE WHEN struct.code IN %(additional_income_structures)s
                THEN hp.health_insurance_contribution_pct_additional_income
                ELSE hp.health_insurance_contribution_pct END
            ) ELSE (
                CASE WHEN hpl.code = 'DMIO1B'
                THEN hp.dmio1b_percentage
                ElSE hp.dmio2b_percentage END
            ) END as percentage,
            SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            LEFT JOIN hr_payroll_structure AS struct ON (hp.struct_id = struct.id)
            WHERE hpl.code IN %(doprinosi_na_placu)s AND hpr.id {0}
            AND hd.id {1}
            AND hpl.total <> 0 GROUP BY hpl.name, percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall()
        total = self.get_totals(res)
        res.append((u'Ukupno doprinosi na plaće', '', total, '', 'total'))
        return res

    def get_totals(self,res):
        total = 0
        for index,el in enumerate(res):
            el = list(el)
            el.append('line')
            el = tuple(el)
            res[index] = el 
            total += el[2]
        return total

    def get_taxes(self, run_cond, dep_cond):
        porezi = self.env['hr.payroll.salary.rule.configuration'].get_rules('porezi')
        porezi = set(porezi)
        code_blacklist = set(self.env['hr.salary.rule'].search([('category_id.code', '=', 'PRIR')]).mapped('code'))
        porezi -= code_blacklist
        porezi = tuple(porezi)
        params = {
            'porezi': porezi,
        }
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code IN %(porezi)s AND hpr.id {0} 
            AND hd.id {1}
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall()    
        porez = 0
        for line in res:
            if line[3] in ['PDOH']:
                porez += line[2]
        res.append(('Ukupno porez', 0.0, porez, '', u'line',))
        return res

    def get_income(self, run_cond, dep_cond):
        dohodak_i_odbitak = self.env['hr.payroll.salary.rule.configuration'].get_rules('dohodak_i_odbitak')
        params = {
            'dohodak_i_odbitak': dohodak_i_odbitak,
        }
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code IN %(dohodak_i_odbitak)s  AND hpr.id {0}
            AND hd.id {1}
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall() 
        return res

    def get_admitted_cost(self, run_cond, dep_cond):
        priznati_izdatak = self.env['hr.payroll.salary.rule.configuration'].get_rules('priznati_izdatak') 
        params = {
            'priznati_izdatak': priznati_izdatak,
        }
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code IN %(priznati_izdatak)s
            AND hpr.id {0}
            AND hd.id {1}
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
            """.format(run_cond, dep_cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall() 
        return res

    def get_neto(self, run_cond, dep_cond):
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            --LEFT JOIN hr_employee AS em ON (c.employee_id = em.id)
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            LEFT JOIN res_partner ON (em.address_home_id = res_partner.id)
            LEFT JOIN res_country_state AS rcs ON (res_partner.state_id = rcs.id)
            WHERE hpl.code  = 'NETO'  AND hpr.id {0}
            AND hd.id {1}
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall() 
        total = self.get_totals(res)
        res.append((u'Ukupno neto plaća', '', total, '', 'total'))
        return [res[-1]]

    def get_suspensions(self, run_cond, dep_cond):
        obustave = self.env['hr.payroll.salary.rule.configuration'].get_rules('obustave')
        params = {
            'obustave': obustave,
        }
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_payslip AS hp
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code in %(obustave)s  AND hpr.id {0}
            AND hd.id {1}
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall()  
        total = self.get_totals(res)
        res.append((u'Ukupno', '', total, '', 'total'))     
        return res

    def get_payment(self, run_cond, dep_cond):
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code IN ('ISPL')  AND hpr.id {0}
            AND hd.id {1} 
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall() 
        return res

    def get_work_abroad_hr(self, run_cond, dep_cond):
        izaslani_porez_u_HR = self.env['hr.payroll.salary.rule.configuration'].get_rules('izaslani_porez_u_HR')
        params = {
            'izaslani_porez_u_HR': izaslani_porez_u_HR,
        }
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code IN %(izaslani_porez_u_HR)s  AND hpr.id {0}
            AND hd.id {1}
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall() 
        return res
        
    def get_work_abroad_ino(self, run_cond, dep_cond):
        izaslani_porez_ino_neto = self.env['hr.payroll.salary.rule.configuration'].get_rules('izaslani_porez_ino_neto')
        params = {
            'izaslani_porez_ino_neto': izaslani_porez_ino_neto,
        }
        query = """
            SELECT DISTINCT(hpl.name), hpl.amount_percentage, SUM(hpl.total), hpl.code, 'line',hpl.sequence
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_line AS hpl ON (hp.id = hpl.slip_id)
            WHERE hpl.code IN %(izaslani_porez_ino_neto)s  AND hpr.id {0}
            AND hd.id {1}
            AND hpl.total <> 0 GROUP BY hpl.name, hpl.amount_percentage, hpl.code, hpl.sequence
            ORDER BY hpl.sequence
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query, params)
        res = self.env.cr.fetchall() 
        return res
