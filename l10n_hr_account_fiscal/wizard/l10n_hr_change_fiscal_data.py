from odoo import fields, models, api, _
from odoo.exceptions import UserError


class L10nHrChangeFiscalData(models.TransientModel):
    _name = "l10n_hr.change.fiscal.data"
    _description = 'Change Fiscal Data Wizard'

    l10n_hr_payment_method = fields.Selection(
        selection=[("G", "Cash"),
                   ("K", "Credit or debit cards"),
                   ("T", "Bank transfer"),
                   ("O", "Other payment means"),
                   ],
        string="Croatia - Payment Method",
        help="According to Fiscalization Law and regulative "
             "there are 4 possible options: \n"
             "G - Cash (coins or bills), fiscalization required\n"
             "K - Bank cards, fiscalization required\n"
             "T - Transaction bank account\n"
             "O - Other payment, fiscalization required\n")
    partner_id = fields.Many2one('res.partner', 'Customer')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_model, active_id = self.env.context.get('active_model'), self.env.context.get('active_id')
        current_move = self.env[active_model].browse(active_id)
        res.update(dict(l10n_hr_payment_method=current_move.l10n_hr_payment_method,
                        partner_id=current_move.partner_id.id))
        return res

    def change(self):
        active_model, active_id = self.env.context.get('active_model'), self.env.context.get('active_id')
        current_move = self.env[active_model].browse(active_id)
        new_vals = dict()
        if current_move.partner_id != self.partner_id:
            new_vals.update(partner_id=self.partner_id and self.partner_id.id or False)
        if current_move.l10n_hr_payment_method != self.l10n_hr_payment_method:
            new_vals.update(l10n_hr_payment_method=self.l10n_hr_payment_method)
        if not new_vals:
            raise UserError(_('Nothing to change!'))
        response = current_move.fiscalize_data_change(self.partner_id, self.l10n_hr_payment_method)
        # if response contains errors from FINA, do not commit changes
        if response and not response.Greske:
            current_move.with_context(skip_readonly_check=True).write(new_vals)
        return True
