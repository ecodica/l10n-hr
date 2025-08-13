from odoo import fields, models, api


class AccountMove(models.Model):
    ''' Extension to add Tip fields to invoice. '''
    _inherit = 'account.move'

    @api.model
    def get_l10n_hr_account_payment_type_as_selection_options(self):
        payment_types = self.env['l10n_hr.account.payment.type'].search([])
        if payment_types:
            return [(pt.code, pt.name) for pt in payment_types]
        return [('', '')]

    def _get_default_l10n_hr_account_payment_type_id_code(self):
        default_journal_payment_type = self.journal_id.l10n_hr_default_account_payment_type_id
        return default_journal_payment_type and default_journal_payment_type.code or ''


    l10n_hr_napojnica_iznos = fields.Monetary(
        string='Tip Amount',
        currency_field='currency_id')

    l10n_hr_napojnica_nacin_placanja = fields.Selection(
        selection=lambda self: self.get_l10n_hr_account_payment_type_as_selection_options(),
        string="Tip Payment Method",
        default=lambda self: self._get_default_l10n_hr_account_payment_type_id_code()
    )

    l10n_hr_enable_tips_on_invoice = fields.Boolean(
        related='company_id.l10n_hr_enable_tips_on_invoice',
    )
