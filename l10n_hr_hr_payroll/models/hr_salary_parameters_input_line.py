# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api , _
from odoo.exceptions import ValidationError


class HrSalaryParametersInputLine(models.Model):
    """
    This class is used to define salary rules which will be copied as payslip inputs
    when a payslip for employee is created.
    """

    _name = 'hr.salary.parameters.input.line'
    _description = "Stavka dodatka na plaću za parametre plaće"

    def _get_input_categories_domain(self):
        category_codes = self.env['hr.payroll.salary.rule.category.configuration'].get_category('inputs_categories') or []
        return [('category_id.code', 'in', category_codes)]

    parameters_id = fields.Many2one('hr.salary.parameters', required=True, ondelete='cascade')
    rule_id = fields.Many2one('hr.salary.rule', required=True, domain=lambda self: self._get_input_categories_domain(),string='Pravilo')
    amount = fields.Float('Iznos')
