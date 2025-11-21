# -*- coding: utf-8 -*-
##############################################################################

##############################################################################

import time
from datetime import datetime
from dateutil import relativedelta
from ..models import payroll_common as paycom
from odoo import fields, _, models, api

class HrPayslipAddInputsWizardLine(models.TransientModel):
    _name ='hr.payslip.add.inputs.wizard.line'
    _description = 'Stavka zaposlenika za formu za unos dodataka'

    def _input_code_selection(self):
        self.env.context = self.env.context or {}
        res={}
        category_obj = self.env['hr.salary.rule.category']
        category_ids = category_obj.search([('code', 'in', self.env['hr.payroll.salary.rule.category.configuration'].get_category('inputs_categories'))])
        rule_obj = self.env['hr.salary.rule']
        if category_ids:
            ids = rule_obj.search([('category_id','in',category_ids.ids),])                    
            rules = rule_obj.browse(ids)
            res = [(r['code'], r['code']) for r in rules.ids]
        res = sorted(res)
        return res

    wizard_id = fields.Many2one('hr.payslip.add.inputs.wizard', 'Wizard id')
    employee_id = fields.Many2one('hr.employee', 'Zaposlenik')
    payslip_id = fields.Many2one('hr.payslip', 'Isplatni listić')
    contract_id = fields.Many2one('hr.contract', 'Ugovor')
    code = fields.Selection(_input_code_selection, 'Šifra')
    amount =  fields.Float('Iznos')


class HrPayslipAddInputsWizard(models.TransientModel):

    _name ='hr.payslip.add.inputs.wizard'
    _description = 'Generiraj ulazne parametri za sve odabrane zaposlenike'
    
    def _input_code_selection(self):
        return self.env['hr.payslip.input']._input_code_selection()
    
    run_id = fields.Many2one('hr.payslip.run', 'Obračun plaće')
    code = fields.Selection(_input_code_selection, 'Šifra', required=True)
    amount = fields.Float('Iznos', help="It is used in computation. For e.g. A rule for sales having 1% commission of basic salary for per product can defined in expression like result = inputs.SALEURO.amount * contract.wage*0.01.")
    name = fields.Char('Opis', required=True)
    employee_ids = fields.One2many('hr.payslip.add.inputs.wizard.line', 'wizard_id', 'Zaposlenici')


    @api.model
    def default_get(self, fields):
        res = super(HrPayslipAddInputsWizard, self).default_get(fields)
        employees = []
        if 'active_id' in self.env.context and self.env.context['active_id']:
            res['run_id'] = self.env.context['active_id']
            payslip_obj = self.env['hr.payslip']
            payslip_ids = payslip_obj.search([('payslip_run_id','=',res['run_id'])])
            for payslip in payslip_ids:
                employees.append({
                    'employee_id': payslip.employee_id.id,
                    'payslip_id':payslip.id,
                    'amount':0.0,
                    'contract_id':payslip.contract_id.id
                    })
            res['employee_ids'] = [(0,0,line) for line in employees]
        return res
    
    def add_inputs_on_payslip(self):
        input_obj = self.env['hr.payslip.input']
        values = {}
        name = self.name
        code = self.code
        for line in self.employee_ids:
            values.update({
                'payslip_id': line.payslip_id.id,
                'contract_id': line.contract_id.id,
                'code': code,
                'name': name,
                'amount': line.amount
            })
            if line.code == 'PRV':
                line.payslip_id.write({'manual_input':True})
            payslip_input_ids = input_obj.search([('payslip_id','=',line.payslip_id.id),('code','=',code)])
            payslip_input_ids.unlink()
            if values['amount'] > 0:
                input_obj.create(values)
        return True

    @api.onchange('code', 'amount')
    def onchange_amount(self):
        input_obj = self.env['hr.payslip.input']
        result = {'value':{}}
        employees = {}
        employees_list = []
        if self.amount or self.code:
            name = ''
            if self.code:
                name = input_obj.get_rule_name(self.code)
            for line in self.employee_ids:
                line.amount = self.amount if self.amount else 0
                line.code = self.code if self.code else False
            self.name = name