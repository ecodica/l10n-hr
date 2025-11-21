# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class EmployeeBankAccountLine(models.Model):
    """
    This class is used as bank account overview for employee.
    An instance of res.partner.bank needs to be created first (which implies res.partner as well).
    Only bank accounts from employee's partner (partner_id field in hr.employee class) can be entered here.
    System user has read access so they are able to open employee form view.
    Payroll officer has all acess rights.
    """
    _name = 'employee.bank.account.line'
    _description = 'Stavka prikaza bankovnih račun zaposlenika'
    _order = 'date_from DESC'
    _inherit ='mail.thread'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='ID zaposlenika', ondelete='cascade')

    bank_account_id = fields.Many2one(comodel_name='res.partner.bank', string='Račun isplate',tracking=True)
    account_number = fields.Char(string='Broj računa', related='bank_account_id.acc_number', tracking=True)
    bank_name = fields.Char(string='Banka', related='bank_account_id.bank_name', tracking=True)
    account_type = fields.Selection(string='Tip računa', default='normal',
        selection=[('normal', 'Redovni'), ('protected', 'Zaštićeni'), ('giro_account', 'Žiro račun')],
        help='Tip računa zaposlenika.', tracking=True)

    main_account = fields.Boolean(string='Primarni račun', tracking=True)
    date_from = fields.Date(string='Od datuma', tracking=True)
    date_to = fields.Date(string='Do datuma', tracking=True)
