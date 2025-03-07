from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_payment_order_communication_direct(self):
        super()._get_payment_order_communication_direct()
        if self.is_invoice():
            if self.is_purchase_document():
                communication = self.payment_reference
        return communication or ""