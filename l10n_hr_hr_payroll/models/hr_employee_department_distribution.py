# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class DepartmentAnaylticDistribution(models.Model):
    _name = "hr.employee.department.distribution"
    _description = "Analitička raspodjela troškova zaposlenika po odjelima"
    _order = "id desc"
    
    employee_id = fields.Many2one('hr.employee', 'Zaposlenik', ondelete='cascade')
    department_analytic_id = fields.Many2one('account.analytic.account', 'Odjel', required=True)
    cost_center_id = fields.Many2one('account.analytic.account', 'Mjesto troška')
    # field is used for calculations in payroll - higher precision is required
    percentage = fields.Float('Postotak', digits=(12,8))