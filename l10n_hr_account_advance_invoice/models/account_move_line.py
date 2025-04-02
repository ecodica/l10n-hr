from odoo import api, fields, models, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def write(self, vals):
        #if advance move -> update account_id on payment_term line
        records = super().write(vals)
        for move_line in self.filtered(lambda line: line.move_id.advance_invoice):
            for line in move_line.filtered(lambda line: line.display_type == 'payment_term' and line.account_id != move_line.move_id.advance_account_id):
                line.account_id = move_line.move_id.advance_account_id
        return records
