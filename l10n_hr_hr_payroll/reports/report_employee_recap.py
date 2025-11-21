# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from ..models import payroll_common as paycom


class EmployeeRecapReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_employee_recap'
    _description = 'Employee recap report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        run_ids = data.get('active_ids', data.get('run_ids'))
        runs = self.env['hr.payslip.run'].browse(run_ids)

        if data.get('emp_ids'):
            emps = self.env['hr.employee'].browse(data['emp_ids'])
        else:
            emps = self.env['hr.employee'].with_context(active_test=False).search([])
            
        run_names = [run.name for run in runs]
        run_names_couples = []
        if len(run_names) > 6:
            run_names_couples = self.get_payslip_run_name_couples(run_names)
        emp_lines = self.get_payslip_lines_totals(runs, emps)
        sum_line = self.get_sum_line(emp_lines)
        prec = self.env['decimal.precision'].precision_get('Payroll')
        period = data.get('period',{})
        return {
            'company': self.env.user.company_id,
            'emp_lines': emp_lines,
            'sum_line': sum_line,
            'prec': prec,
            'run_names': run_names,
            'run_names_couples': run_names_couples,
            'period': period
        }
    
    def get_payslip_run_name_couples(self, run_names):
        """
        Create name couples to display in 2-column table in case list is long (so it doesn't use too much space)
        """
        if len(run_names) % 2:
            run_names.append('')
        return [(run_names[2*i], run_names[2*i + 1]) for i in range(int(len(run_names) / 2))]

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
        work_abroad_ino_tax_struct_codes = paycom.get_structures()['work_abroad_ino_tax']
        structures_with_contributions_only_codes = paycom.get_structures()['contributions_only']

        # this section is copied from report_hr_payslip_run -> keep in sync        
        struct_obj = self.env['hr.payroll.structure']
        structures_with_contributions_only_ids = struct_obj.search([('code', 'in', structures_with_contributions_only_codes)]).ids
        structures_with_contributions_only = tuple(structures_with_contributions_only_ids)
        work_abroad_ino_tax_struct_ids = struct_obj.search([('code', 'in', work_abroad_ino_tax_struct_codes)]).ids
        work_abroad_ino_tax_struct = tuple(work_abroad_ino_tax_struct_ids)
        exception_struct_ids = structures_with_contributions_only + work_abroad_ino_tax_struct
        payroll_conf = self.env['hr.payroll.salary.rule.configuration']
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
            'structures_with_contributions_only': structures_with_contributions_only,
            'doprinosi': doprinosi,
            'work_abroad_ino_tax_struct': work_abroad_ino_tax_struct,
            'work_abroad_ino_tax_rules': work_abroad_ino_tax_rules,
            'payslip_run_condition': payslip_run_condition,
            'emp_condition': emp_condition,
        }
        query = """
            SELECT
            ROW_NUMBER() OVER(ORDER BY em.name) AS Row,
            em.emp_name AS emp_name,
            em.emp_first_name AS emp_first_name,
            em.emp_last_name AS emp_last_name,
            em.emp_code AS emp_code,
            SUM(osnovica) AS osnovica,
            SUM(mioi) AS mio1,
            SUM(mioii) AS mio2,
            SUM(doh) AS doh,
            SUM(porosn) AS porosn,
            SUM(pdoh) AS pdoh,
            SUM(neto) AS neto,
            SUM(obs) AS obs,
            SUM(dodn) AS dodn,
            SUM(ispl) AS ispl,
            SUM(dopna) AS dopna,
            SUM(brutto2) AS brutto2
            FROM (
                SELECT em.name,
                CONCAT(em.first_name, ' ', em.last_name) as emp_name,
                em.first_name as emp_first_name,
                em.last_name as emp_last_name,
                em.code as emp_code,
                SUM(CASE WHEN hrs.code = 'BASIC' THEN  hpl.total ELSE 0 END) Osnovica,
                SUM(CASE WHEN hrs.code IN ('DMIO1','DMIOU1') THEN hpl.total ELSE 0 END) MIOI ,
                SUM(CASE WHEN hrs.code IN ('DMIO2','DMIOU2') THEN hpl.total ELSE 0 END) MIOII ,
                SUM(CASE WHEN hrs.code = 'DOH' THEN hpl.total ELSE 0 END) DOH  ,
                SUM(CASE WHEN hrs.code = 'POROSN' THEN hpl.total ELSE 0 END) POROSN  ,
                SUM(CASE WHEN hrs.code = 'PDOH' THEN hpl.total ELSE 0 END) PDOH ,
                SUM(CASE WHEN hrs.code = 'NETO' THEN hpl.total ELSE 0 END) NETO  ,
                SUM(CASE WHEN hrs.code in ('OBS','TOPOB','MSPORT') THEN hpl.total ELSE 0 END) OBS  ,
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
                GROUP BY emp_name, em.name, em.code, em.first_name, em.last_name, hrs.code, hpl.total
                ORDER BY em.name
            ) AS em
            GROUP BY em.name, em.emp_name, em.emp_code, em.emp_first_name, em.emp_last_name
        """.format(structures_with_contributions_only, payslip_run_condition, emp_condition)
        self._cr.execute(query, params)
        res = self._cr.dictfetchall()
        return res
        
    def get_sum_line(self, emp_lines):
        FIELDS_TO_SUM = ['osnovica','mio1','mio2','doh','porosn','pdoh','neto','obs','dodn','ispl','dopna','brutto2']
        res = dict()
        for field in FIELDS_TO_SUM:
            res.update({field: 0})
        for line in emp_lines:
            for field in FIELDS_TO_SUM:
                res[field] += line[field]
        return [res]
