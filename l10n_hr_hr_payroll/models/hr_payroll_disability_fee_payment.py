# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HrPayrollDisabilityFeePayment(models.Model):
    _name = 'hr.payroll.disability.fee.payment'
    _description = "Ova klasa se koristi za isplatu naknade za nezapošljavanje OSI"
    _rec_name = 'payslip_run_id'

    payslip_run_id = fields.Many2one('hr.payslip.run', 'Obračun plaće', required=True)
    minimal_wage = fields.Float('Minimalna plaća')
    disability_fee_pct = fields.Float('Udio minimalne plaće za obračun naknade (%)')
    emps_with_disabilities_quota_pct = fields.Float('Potreban udio zaposlenih OSI (%)')
    min_number_of_emps_with_disabilities = fields.Integer('Potreban broj zaposlenih OSI')
    disability_fee_amount = fields.Float('Iznos naknade za OSI')
    number_of_emps_total = fields.Integer('Ukupan broj zaposlenika')
    number_of_emps_with_disabilities = fields.Integer('Broj zaposlenih OSI')
    min_total_number_of_emps_to_pay_fee = fields.Integer('Minimalni broj zaposlenika za obračunavanje naknade')
    disability_fee_number_of_emps = fields.Integer('Broj zaposlenika za koje se plaća naknada', compute='get_disability_fee_number_of_emps')
    state = fields.Selection([('draft', 'Nacrt'), ('paid', 'Plaćeno')], 'Stanje', default='draft')
    credit_disability_fee = fields.Boolean('Knjiži naknadu za OSI', default=True)
    disability_fee_credit_account_id = fields.Many2one('account.account', 'Potražni konto')
    disability_fee_debit_account_id = fields.Many2one('account.account', 'Dugovni konto')
    company_id = fields.Many2one('res.company', 'Tvrtka', required=True,
                                default=lambda self: self.env.company, index=True)


    @api.depends('number_of_emps_with_disabilities', 'min_number_of_emps_with_disabilities')
    def get_disability_fee_number_of_emps(self):
        for fee in self:
            number_of_emps = fee._calculate_number_of_emps_for_disability_fee(fee.min_number_of_emps_with_disabilities, fee.number_of_emps_with_disabilities)
            fee.disability_fee_number_of_emps = number_of_emps

    def _calculate_employee_quota(self, emps_total, min_required_emps, quota_pct):
        if emps_total < min_required_emps:
            return 0
        return round(emps_total * quota_pct / 100.0, 0)

    def _calculate_disability_fee_amount(self, minimal_wage, disability_fee_pct, disability_fee_number_of_emps):
        amount = disability_fee_number_of_emps * minimal_wage * disability_fee_pct / 100.0
        return amount
    
    @api.onchange('number_of_emps_total', 'min_total_number_of_emps_to_pay_fee', 'emps_with_disabilities_quota_pct')
    def onchange_update_employee_quota(self):
        emps_total = self.number_of_emps_total
        min_required_emps = self.min_total_number_of_emps_to_pay_fee
        quota_pct = self.emps_with_disabilities_quota_pct
        quota = self._calculate_employee_quota(emps_total, min_required_emps, quota_pct)
        self.min_number_of_emps_with_disabilities = quota

    @api.onchange('minimal_wage', 'disability_fee_pct', 'disability_fee_number_of_emps')
    def onchange_update_disability_fee_amount(self):
        amount = self._calculate_disability_fee_amount(self.minimal_wage, self.disability_fee_pct, self.disability_fee_number_of_emps)
        self.disability_fee_amount = amount
    
    @api.onchange('min_number_of_emps_with_disabilities', 'number_of_emps_with_disabilities')
    def onchange_update_disability_fee_number_of_emps(self):
        self.disability_fee_number_of_emps = self._calculate_number_of_emps_for_disability_fee(self.min_number_of_emps_with_disabilities, self.number_of_emps_with_disabilities)

    def _calculate_number_of_emps_for_disability_fee(self, min_required_emps, emps_with_disabilities):
        return max(min_required_emps - emps_with_disabilities, 0)

    def pay_disability_fee(self):
        return self.write({'state': 'paid'})

    def draft_disability_fee(self):
        return self.write({'state': 'draft'})

    @api.onchange('payslip_run_id')
    def onchange_payslip_run_id(self):
        if self.payslip_run_id:
            data = self.payslip_run_id.get_disability_fee_data()
            self.minimal_wage = data['minimal_wage']
            self.disability_fee_pct = data['disability_fee_pct']
            self.emps_with_disabilities_quota_pct = data['emps_with_disabilities_quota_pct']
            self.min_number_of_emps_with_disabilities = data['min_number_of_emps_with_disabilities']
            self.disability_fee_amount = data['disability_fee_amount']
            self.number_of_emps_total = data['number_of_emps_total']
            self.number_of_emps_with_disabilities = data['number_of_emps_with_disabilities']
            self.min_total_number_of_emps_to_pay_fee = data['min_total_number_of_emps_to_pay_fee']
            self.disability_fee_number_of_emps = data['disability_fee_number_of_emps']
            self.credit_disability_fee = data['credit_disability_fee']
            self.disability_fee_credit_account_id = data['disability_fee_credit_account_id']
            self.disability_fee_debit_account_id = data['disability_fee_debit_account_id']