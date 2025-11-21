# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HrContractTaxDeduction(models.Model):
    _name = 'hr.contract.tax.deduction'
    _description = "Linija poreznog odbitka za model parametara plaće"

    salary_parameters_id = fields.Many2one('hr.salary.parameters', required=True, ondelete='cascade')
    tax_deduction_id = fields.Many2one('tax.deduction', required=True, string="Osobni odbitak")
    sequence = fields.Integer(related="tax_deduction_id.sequence")
    qty = fields.Float(string='Količina')
    tax_deduction_coef = fields.Float(string='Koeficijent', compute='_get_tax_deduction_coef', store=True)
    status = fields.Boolean(string='Status')
    deduction_shared_with = fields.Char(string='Dijeljeno s')

    @api.depends('qty','tax_deduction_id')
    def _get_tax_deduction_coef(self):
        for deduction in self:
            deduction.tax_deduction_coef = deduction.qty * deduction.tax_deduction_id.tax_deduction_coef
