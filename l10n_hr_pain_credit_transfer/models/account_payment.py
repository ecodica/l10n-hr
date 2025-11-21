# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_payment_desc(self):
        def _get_payment_info(payment_line):
            return payment_line.move_line_id.move_id and \
                   (payment_line.move_line_id.move_id.ref or
                    payment_line.move_line_id.move_id.name or '') or \
                   payment_line.communication
        self.ensure_one()
        payment_desc = ''
        for line in self.payment_line_ids:
            payment_desc += _get_payment_info(line)
        if not payment_desc:
            payment_desc = '-'
        return payment_desc
