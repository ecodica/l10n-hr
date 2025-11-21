# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HRPayslipRunSuspensionsReport(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_hr_payslip_run_suspensions'
    _description = 'Payslip run suspensions report'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        doc_ids = data.get('run_ids', doc_ids)
        dep_ids = data.get('department_ids')
        if not dep_ids:
            active_payslip_run = self.env['hr.payslip.run'].search([('id', 'in', doc_ids)])
            dep_ids = active_payslip_run.mapped('slip_ids').mapped('employee_id').mapped('department_id').ids

        doc_model = 'hr.payslip.run'
        docs = self.env[doc_model].browse(doc_ids)
        dep_cond = self.get_conds(dep_ids)
        run_cond = self.get_conds(doc_ids)
        report_data = {}

        report_data = {'suspension_lines': self.get_suspension_lines(run_cond, dep_cond)}
        report_data.update({'company': self.env.user.company_id})
        report_data.update({'run_names': [{'name': doc.name} for doc in docs]})
        return {
            'doc_ids': doc_ids,
            'doc_model': doc_model,
            'docs': docs,
            'data': report_data,
        }

    def get_conds(self, dep_ids):
        cond = "IN ({0})".format(','.join([str(x) for x in dep_ids]))
        return cond
    
    def get_suspension_lines(self, run_cond, dep_cond):
        """
        Read suspension lines from payslips on payslip run.
        """
        query = """
            SELECT
            em.name,
            susp.description,
            bank.acc_number,
            sum(susp.amount) as amount,
            em.code
            FROM hr_employee AS em
            LEFT JOIN hr_payslip AS hp ON (em.id = hp.employee_id)
            LEFT JOIN hr_department AS hd ON (hp.department_id = hd.id)
            LEFT JOIN hr_payslip_run AS hpr ON (hp.payslip_run_id = hpr.id)
            LEFT JOIN hr_payslip_suspension_line AS susp ON (susp.payslip_id = hp.id)
            LEFT JOIN res_partner_bank AS bank ON (bank.id = susp.bank_account_id)
            WHERE hpr.id {0} AND susp.amount > 0 AND hd.id {1}
            GROUP BY em.code, em.name, susp.description, bank.acc_number
            ORDER BY em.name
        """.format(run_cond, dep_cond)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        return res
