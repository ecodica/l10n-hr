# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class EmployeeTaxlessPaymentLine(models.Model):
    """
    This class is used as an overview of employee's taxless payments.
    When payslip (run) is paid, taxless payments are created for each employee.
    System user and payroll officer have read access so they are able to open employee form view.
    Payroll manager has all access rights.
    The tab is visible to payroll officer.
    """
    _name = 'employee.taxless.payment.line'
    _description = "Koristi se za praćenje neoporezivih isplata po zaposleniku"
    _order = 'payment_date DESC'
    
    def _get_taxless_payment_categories_domain(self):
        return [
            ('code', 'in', self.env['hr.payroll.salary.rule.configuration'].get_rules('taxless_payments'))
        ]
    
    employee_id = fields.Many2one('hr.employee', 'Zaposlenik', required=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', 'Obračun plaće')
    payment_amount = fields.Float('Iznos u valuti', required=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', 'Vrsta naknade', domain=lambda self: self._get_taxless_payment_categories_domain())
    payment_date = fields.Date('Datum plaćanja', required=True)
