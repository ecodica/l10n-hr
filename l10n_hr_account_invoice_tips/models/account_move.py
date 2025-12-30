from odoo import fields, models, api


class AccountMove(models.Model):
    ''' Extension to add Tip fields to invoice. '''
    _inherit = 'account.move'

    def _get_default_l10n_hr_account_payment_type_id(self):
        return self.journal_id and self.journal_id.l10n_hr_default_account_payment_type_id

    l10n_hr_napojnica_iznos = fields.Monetary(
        string='Tip Amount',
        currency_field='currency_id',
        copy=False
    )

    l10n_hr_account_tip_payment_type_id = fields.Many2one(
        'l10n_hr.account.payment.type',
        string="Tip Payment Method",
        default=lambda self: self._get_default_l10n_hr_account_payment_type_id()
    )

    l10n_hr_enable_tips_on_invoice = fields.Boolean(
        related='company_id.l10n_hr_enable_tips_on_invoice',
    )
