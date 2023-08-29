# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _prepare_payment_line_vals(self, payment_order):
        vals = super()._prepare_payment_line_vals(payment_order)
        if payment_order.payment_method_id.code == 'sepa_credit_transfer_hr':
            vals.update(communication_type='HR ref')
        return vals
