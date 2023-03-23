from odoo import fields, models, api


class AccountAccount(models.Model):
    _inherit = 'account.account'

    joppd_nontaxable_receipt_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.code.register.nontaxable.receipt',
        string='Non-taxable Receipt',
        ondelete='restrict',
        domain=[('type', '=', 'normal')],
        required=False)
    joppd_payment_method_id = fields.Many2one(
        comodel_name='l10n.hr.joppd.code.register.payment.method',
        string='Payment Method',
        ondelete='restrict',
        domain=[('type', '=', 'normal')],
        required=False)
