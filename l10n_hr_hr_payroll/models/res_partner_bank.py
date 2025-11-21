from odoo import models, api, _
from odoo.exceptions import ValidationError

class ResPartnerBank(models.Model):
    _inherit="res.partner.bank"

    def _get_partners_employees_bank_lines(self):
        employees = self.env['hr.employee'].with_context({'active_test': False}).search([])
        bank_account_lines = employees.mapped('bank_account_ids').filtered(
        lambda l: l.bank_account_id == self and l.employee_id.partner_id == self.partner_id)
        return bank_account_lines
        
    def check_employee_bank_acc_owner(self, values):
        for rec in self:
            if values.get('partner_id', False):
                # don't allow owner change only when bank account owner is same as employee (i.e. bank account partner == employee partner)
                # if the owner is not the same, then we want to allow the change even thought the account is linked to an employee - so that we can fix the owner
                emp_bank_lines = rec._get_partners_employees_bank_lines()
                if emp_bank_lines:
                    raise ValidationError('Zaposlenik {1} je vlasnik bankovnog računa {0}, te se ne može mijenjati!'.format(
                        rec.acc_number, ', '.join(emp_bank_lines.mapped('employee_id').mapped('name'))
                    ))
    
    def write(self, values):
        self.check_employee_bank_acc_owner(values)
        return super(ResPartnerBank, self).write(values)
