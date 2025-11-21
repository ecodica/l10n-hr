# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields

class TaxDeduction(models.Model):
    _name = 'tax.deduction'
    _description = "Šifrarnik osobnih odbitaka"
    _order = 'sequence'

    name = fields.Char(string='Naziv')
    tax_deduction_coef = fields.Float(string='Koeficijent')
    status = fields.Boolean(string='Status')
    sequence = fields.Integer(readonly=True)
