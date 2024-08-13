from odoo import models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def _prepare_move_line_vals(self):
        self.ensure_one()
        res = super(HrExpense, self)._prepare_move_line_vals()
        res.update({'l10n_hr_employee_id': self.employee_id and self.employee_id.id})
        return res
