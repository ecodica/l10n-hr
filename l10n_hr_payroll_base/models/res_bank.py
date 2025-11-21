# -*- coding: utf-8 -*-

import re

import collections

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import pycompat

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    active = fields.Boolean("Active", default=True)
    is_company_account = fields.Boolean('Is company bank account', compute='_compute_is_company_bank_account', store=True)

    @api.onchange('acc_number')
    def onchange_acc_number(self):
        """
        Autocomplete bank based on IBAN if possible.
        Currently supported: Croatian banks with 7-digit leading number.
        """
        if self.acc_number and self.acc_type=='iban' and len(self.acc_number) >= 11:
            leading_numbers = self.env['res.bank']._get_leading_numbers()
            acc_leading_number = self.acc_number[4:11]
            if acc_leading_number in leading_numbers.keys():
                self.bank_id = leading_numbers[acc_leading_number]
    
    @api.depends('partner_id', 'company_id')
    def _compute_is_company_bank_account(self):
        """ Compute if company is the bank account owner."""
        company_list = self.env['res.company'].search([]).mapped('partner_id')
        for bank in self:
            if bank.partner_id in company_list:
                bank.is_company_account = True



class ResBank(models.Model):
    _inherit = 'res.bank'

    leading_number = fields.Char("Leading number", size=7, help="A sequence of digits at the start of every bank account number from this bank. Used to autocomplete bank based on account number.")
    # update help
    bic = fields.Char(help="Sometimes called BIC or Swift. Needed for SEPA file creation in payroll module.")

    @api.model
    def _get_leading_numbers(self):
        """
        Return {leading_number: bank_id} mapping to be used for linking bank account to bank.
        """
        res = {}
        for bank in self.search([]):
            res.update({bank.leading_number: bank.id})
        return res
