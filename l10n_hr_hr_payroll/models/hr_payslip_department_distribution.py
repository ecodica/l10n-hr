# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class PayslipDepartmentDistribution(models.Model):
    """
    This class is a copy of employee department distribution.
    It is used as a setting for payroll crediting and to keep history of department distribution.
    """
    _name = "hr.payslip.department.distribution"
    _description = "Raspodjela po odjelima za zaposlenika"
    
    payslip_id = fields.Many2one('hr.payslip', 'Isplatni listić', ondelete='cascade')
    department_analytic_id = fields.Many2one('account.analytic.account', 'Odjel', required=True)
    cost_center_id = fields.Many2one('account.analytic.account', 'Mjesto troška')
    percentage = fields.Float('Postotak', digits=(12,8))