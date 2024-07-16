from odoo import models

class PosOrder(models.Model):
    """ Extend pos.order model """
    _inherit = 'pos.order'

    def _create_invoice(self, move_vals):
        ''' Override method to manually trigger the computation of fiskal devices on creation of invoice from POS order. '''
        new_move = super()._create_invoice(move_vals)
        new_move._compute_allowed_fiskal_device()
        return new_move
