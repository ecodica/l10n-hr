# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class HrPayrollAccountingSchemeType(models.Model):
    _name = "hr.payroll.accounting.scheme.type"
    _description = "Vrsta sheme knjiženja plaće"
    
    name = fields.Char('Naziv', required=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Naziv vrste knjiženja mora biti jedinstven'),
    ]
