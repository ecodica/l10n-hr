from odoo import models


class PosOrder(models.Model):
    """"Extend to update fiskal_user_id on invoice."""
    _inherit = 'pos.order'

    def _prepare_invoice_vals(self):
        """Extend to set fiskal_user_id from partner related to the employee"""
        move_vals = super()._prepare_invoice_vals()
        if self.employee_id.work_contact_id:
            move_vals['l10n_hr_fiskal_user_id'] = self.employee_id.work_contact_id.id
        return move_vals
