# -*- coding: utf-8 -*-
##############################################################################

##############################################################################

from odoo import fields, _, models, api
from odoo.exceptions import UserError

class AnnualCalculationWizard(models.TransientModel):
    _name ='annual.calculation.wizard'
    _description = 'Čarobnjak za godišnji odmor'

    employee_ids = fields.Many2many('hr.employee','calculation_employee_rel', 'calculation_id', 'employee_id',string='Zaposlenici')

    def do_annual_calculation(self):
        [data] = self.read()     
        context_value = self.env.context.get('payslip_run_id')
        payslip_run_id = self.env['hr.payslip.run'].search([('id', '=', context_value)])
        employee_recs = self.env['hr.employee'].browse(data['employee_ids'])
        employee_ids = [record.id for record in employee_recs]
        return payslip_run_id.annual_calculation(employees=employee_ids, tolerance=payslip_run_id.payslips_without_tax_return_tolerance)
