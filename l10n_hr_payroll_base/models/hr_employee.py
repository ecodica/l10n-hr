# -*- coding:utf-8 -*-

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Payslips', readonly=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count', groups="l10n_hr_payroll_base.group_hr_payroll_user")
    code = fields.Char(string='Code', copy=False) # dodano jer se na reportu 'Popis zarada ispisuje sifra zaposlenika'
    address_home_id = fields.Many2one(
        'res.partner', 'Private Address', help='Enter here the private address of the employee, not the one linked to your company.',
        groups="hr.group_hr_user")

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)
