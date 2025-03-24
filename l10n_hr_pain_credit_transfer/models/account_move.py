from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_payment_order_communication_direct(self):
        super()._get_payment_order_communication_direct()
        if self.is_invoice() and self.is_purchase_document():
           return self.payment_reference or 'HR99'