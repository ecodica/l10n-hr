# -*- coding: utf-8 -*-

from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models, _
from ..models import payroll_common as paycom
from datetime import datetime

_COLS_TO_SUM = 11 # number of (consecutive) columns in report which will be summed


class EmployeeAverageSalaryReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_employee_average_salary'
    _description = 'Employee average salary report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        runs = self.env['hr.payslip.run'].browse(data.get('run_ids'))
        emps = self.env['hr.employee'].browse(data.get('emp_ids'))
        period = data.get('period')

        emp_lines = self.get_payslip_lines_totals(runs, emps)
        emp_lines_grouped = self.group_employee_lines(emp_lines)
        sum_lines = self.add_employee_sums(emp_lines_grouped, period)
        prec = self.env['decimal.precision'].precision_get('Payroll')
        return {
            'docs': self.env['hr.employee'].browse(emp_lines_grouped.keys()),
            'company': self.env.user.company_id,
            'emp_lines': emp_lines_grouped,
            'sum_line': sum_lines,
            'prec': prec,
            'period': period,
        }
    
    def group_employee_lines(self, emp_lines):
        emp_lines_grouped = dict()
        for line in emp_lines:
            emp_id = line[-1]
            if emp_id not in emp_lines_grouped:
                emp_lines_grouped[emp_id] = list()
            emp_lines_grouped[emp_id].append(line)
        return emp_lines_grouped
    
    def get_query_condition(self, ids):
        if len(tuple(set(ids))) == 1:
            cond = "= " + str(ids[0])
        else:
            cond = "IN " + str(tuple(set(ids)))
        return cond

    def get_payslip_lines_totals(self, runs, emps):
        """
        Brutto2 calculation is copied from report_batch and should be kept in sync.
        """
        payroll_conf = self.env['hr.payroll.salary.rule.configuration']
        dodaci_neto_bez_putnih = payroll_conf.get_rules('dodaci_neto_bez_putnih') 
        obustave = payroll_conf.get_rules('obustave') 
        work_abroad_ino_tax_struct_codes = paycom.get_structures()['work_abroad_ino_tax']
        structures_with_contributions_only_codes = paycom.get_structures()['contributions_only']

        # this section is copied from report_hr_payslip_run -> keep in sync        
        struct_obj = self.env['hr.payroll.structure']
        structures_with_contributions_only_ids = struct_obj.search([('code', 'in', structures_with_contributions_only_codes)]).ids
        structures_with_contributions_only = tuple(structures_with_contributions_only_ids)
        work_abroad_ino_tax_struct_ids = struct_obj.search([('code', 'in', work_abroad_ino_tax_struct_codes)]).ids
        work_abroad_ino_tax_struct = tuple(work_abroad_ino_tax_struct_ids)
        exception_struct_ids = structures_with_contributions_only + work_abroad_ino_tax_struct
        brutto_2 = payroll_conf.get_rules('brutto_2')      
        doprinosi_iz_place = payroll_conf.get_rules('doprinosi_iz_place')
        doprinosi_na_placu = payroll_conf.get_rules('doprinosi_na_placu')
        izaslani_porez_ino_neto = payroll_conf.get_rules('izaslani_porez_ino_neto')
        neto_dodaci = payroll_conf.get_rules('dodaci_neto')
        bolovanje_fond = payroll_conf.get_rules('bolovanje_fond')
        doprinosi = doprinosi_iz_place + doprinosi_na_placu
        work_abroad_ino_tax_rules = doprinosi + izaslani_porez_ino_neto + neto_dodaci + bolovanje_fond
        # end of section

        payslip_run_condition = self.get_query_condition(runs.ids)
        emp_condition = self.get_query_condition(emps.ids)
        structures_with_contributions_only = self.get_query_condition(structures_with_contributions_only_ids)
        params = {
            'neto_dodaci': neto_dodaci,
            'doprinosi_na_placu': doprinosi_na_placu,
            'exception_struct_ids': exception_struct_ids,
            'brutto_2': brutto_2,
            'doprinosi': doprinosi,
            'work_abroad_ino_tax_struct': work_abroad_ino_tax_struct,
            'work_abroad_ino_tax_rules': work_abroad_ino_tax_rules,
        }
        query = """
            SELECT em.run_name as run_name, em.run_date as run_date, SUM(sati),
            SUM(osnovica), SUM(brutto2), SUM(mioi) + SUM(mioii) + SUM(dopna), SUM(doh), SUM(odb), 
            SUM(porosn), SUM(pdoh) + SUM(prir), SUM(neto), SUM(ispl), em.emp_id as emp_id
            FROM (
                SELECT
                em.id as emp_id,
                em.name as emp_name,
                hpr.name as run_name,
                hpr.pay_date as run_date,
                COALESCE(hp.user_work_hours, 0) Sati,
                SUM(CASE WHEN hrs.code = 'BASIC' THEN  hpl.total ELSE 0 END) Osnovica,
                SUM(CASE WHEN hrs.code IN ('DMIO1','DMIOU1') THEN hpl.total ELSE 0 END) MIOI ,
                SUM(CASE WHEN hrs.code IN ('DMIO2','DMIOU2') THEN hpl.total ELSE 0 END) MIOII ,
                SUM(CASE WHEN hrs.code = 'IOOD' THEN hpl.total ELSE 0 END) ODB  ,
                SUM(CASE WHEN hrs.code = 'DOH' THEN hpl.total ELSE 0 END) DOH  ,
                SUM(CASE WHEN hrs.code = 'POROSN' THEN hpl.total ELSE 0 END) POROSN  ,
                SUM(CASE WHEN hrs.code = 'PDOH' THEN hpl.total ELSE 0 END) PDOH ,
                SUM(CASE WHEN hrs.code = 'PRIR' THEN hpl.total ELSE 0 END) PRIR ,
                SUM(CASE WHEN hrs.code = 'NETO' THEN hpl.total ELSE 0 END) NETO  ,
                SUM(CASE WHEN hrs.code in %(neto_dodaci)s THEN hpl.total ELSE 0 END) DODN  ,
                SUM(CASE WHEN hrs.code = 'ISPL' THEN hpl.total ELSE 0 END) ISPL ,
                SUM(CASE WHEN hrs.code in %(doprinosi_na_placu)s THEN hpl.total ELSE 0 END) DOPNA ,
                SUM(
                    CASE WHEN (
                        -- standardni slucaj
                        (hps.id NOT IN %(exception_struct_ids)s AND hpl.code IN %(brutto_2)s) OR
                        -- isplata doprinosa
                        (hps.id {0} AND hpl.code IN %(doprinosi)s) OR
                        -- izaslani rad s porezom u inozemstvu 
                        -- racunamo sve osim BASIC jer se na tu osnovicu samo placaju doprinosi, a placa se obracunava po ino satnici
                        (hps.id in %(work_abroad_ino_tax_struct)s AND hpl.code in %(work_abroad_ino_tax_rules)s)
                    ) THEN hpl.total ELSE 0 END                    
                ) BRUTTO2
                FROM hr_employee as em
                LEFT JOIN hr_payslip_line as hpl on (em.id = hpl.employee_id)
                LEFT JOIN hr_salary_rule as hrs on (hpl.salary_rule_id = hrs.id)
                JOIN hr_payslip as hp on(hpl.slip_id = hp.id)
                JOIN hr_payslip_run as hpr on(hp.payslip_run_id = hpr.id)
                JOIN hr_payroll_structure AS hps ON (hps.id = hp.struct_id)
                WHERE hpr.id {1} AND hpl.total != 0 AND em.id {2}
                GROUP BY em.id, hpr.id, hp.id
                ORDER BY hpr.pay_date
            ) AS em
            GROUP BY em.run_date, em.run_name, em.emp_id, em.emp_name
            ORDER BY em.emp_name, em.run_date
        """.format(structures_with_contributions_only, payslip_run_condition, emp_condition)
        self._cr.execute(query, params)
        res = self._cr.fetchall()
        return res
    
    def _calc_months(self, period):
        date_to = datetime.strptime(period.get('date_to'), DEFAULT_SERVER_DATE_FORMAT).date()
        date_from = datetime.strptime(period.get('date_from'), DEFAULT_SERVER_DATE_FORMAT).date()
        months = (date_to.year - date_from.year) * 12 + date_to.month - date_from.month + 1
        return months
    
    def add_employee_sums(self, emp_lines, period):
        """
        Returns: {
            employee_id: [
                [list of sums],
                [list of monthly averages],
                [list of hourly averages],
            ]
        }
        """
        months = self._calc_months(period)
        sum_lines = dict()
        # add sum line
        for emp_id in emp_lines:
            sum_lines[emp_id] = [self._sum_line(emp_lines[emp_id])]
        # add avg lines
        for emp_id in sum_lines:
            sum_line = sum_lines[emp_id][0]
            hours = sum_line[1]
            sum_lines[emp_id].append(
                self._get_avg_line(_('Prosjek po mjesecu'), months, sum_line)
            )
            sum_lines[emp_id].append(
                self._get_avg_line(_('Prosjek po satu'), hours, sum_line)
            )
        return sum_lines
    
    def _get_avg_line(self, desc, divisor, sum_line):
        """Returns: ['Description', avg_1, avg_2, ...]"""
        return [desc] + [(float(sum_line[i+1]) / divisor if divisor else 0) for i in range(0, len(sum_line)-1)]
    
    def _sum_line(self, emp_lines):
        sum_line_shift = 1 # index of first "summable" column (i.e. first amount column)
        emp_line_shift = 2 # index of first "summable" column (i.e. first amount column)
        sum_list = [_('Total')] + [0.00] * _COLS_TO_SUM
        for emp_line in emp_lines:
            for i in range(_COLS_TO_SUM):
                sum_list[i + sum_line_shift] += emp_line[i + emp_line_shift]
        return sum_list