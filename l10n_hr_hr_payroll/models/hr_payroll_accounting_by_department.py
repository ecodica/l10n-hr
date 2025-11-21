# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HrPayrollAccountingByDepartment(models.Model):   
    _name = 'hr.payroll.accounting.by.department'
    _description = "Knjiženje po odjelima"

    scheme_id = fields.Many2one('hr.payroll.accounting.scheme', 'Shema', readonly=True)
    department_id = fields.Many2one('hr.department', 'Odjel')
    debit_account_id = fields.Many2one('account.account', 'Debitni račun')
    credit_account_id = fields.Many2one('account.account', 'Kreditni račun')