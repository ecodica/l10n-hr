# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"
    
    def action_post(self):
        """
        When account move is posted check if has link to payslip run, if so change payslip run status.
        Only allow check if user has payroll manager group, else error pops up (no access rights) when posting any account move.
        Trigger analytic tags constraint manually because it has been skipped on create (in pay_payslip_run())
        """
        if self.env.user.has_group('l10n_hr_payroll_base.group_hr_payroll_manager'):
            for move in self:
                payslip_run_obj = self.env['hr.payslip.run']
                run_ids = payslip_run_obj.search([('move_id', '=', move.id)])
                for run in run_ids:
                    run.write({'state': 'posted'})
        return super().action_post()

    def button_cancel(self):
        """
        When account move is canceled check if has link to payslip run, if so change payslip run status.
        """
        result = super().button_cancel()
        payslip_run_obj = self.env['hr.payslip.run']
        for move in self:
            for payslip_run in payslip_run_obj.search([('move_id', '=', move.id)]):
                payslip_run.write({'state': 'paid'})
                payslip_run.move_id.button_draft()
        return result
